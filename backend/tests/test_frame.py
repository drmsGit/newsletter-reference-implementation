"""The snapshot frame (ADR-183): a composition frozen with its values.

Three properties carry the design, each pinned here:
  - **parity** — a frame of an unchanged variant renders exactly what the live
    send-mode render does (ADR-063: one intended output, two paths);
  - **frozen** — edits after the frame do not reach what it renders;
  - **recorded picks** — given the picks a send recorded, a re-render shows
    them even after the slot would now pick something else.
"""
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import (
    create_campaign, create_decision_slot_for_variant, create_module_for_variant,
)
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.content.service import create_content, create_content_version
from app.database import SessionLocal
from app.rendering.frame import build_frame, is_frame, render_frame
from app.rendering.service import render_variant_html


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _published(db, brand, headline):
    record = create_content(db, title=f"frame-{uuid.uuid4().hex[:6]}", brand_id=brand.id,
                            content={"headline_medium": headline, "body_medium": "Body"})
    create_content_version(db, content_record_id=record.id, created_by="test", brand_id=brand.id)
    return record


@pytest.fixture
def world(db):
    """An email variant: a header (subject), a content module, and a slot
    module with a global pick."""
    brand = ensure_default_brand(db)
    campaign = create_campaign(db, name=f"frame-{uuid.uuid4().hex[:6]}", brand_id=brand.id,
                               channel="email")
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    fixed = _published(db, brand, "Fixed headline")
    picked = _published(db, brand, "Picked headline")
    later = _published(db, brand, "Later pick")
    create_module_for_variant(db, variant_id=variant.id, module_type="header",
                              module_data={"subject": "Hello", "preheader": "Peek"},
                              brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="img_right",
                              content_record_id=fixed.id, brand_id=brand.id)
    slot = create_decision_slot_for_variant(db, variant_id=variant.id, name="slot",
                                            brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="single_stack",
                              decision_slot_id=slot.id, brand_id=brand.id)
    db.add(DecisionResolutionDB(decision_slot_id=slot.id, content_record_id=picked.id))
    db.commit()
    yield {"brand": brand, "variant": variant, "fixed": fixed, "picked": picked,
           "later": later, "slot_id": slot.id}
    db.rollback()
    records = [fixed.id, picked.id, later.id]
    db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id == slot.id).delete()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(DecisionSlotDB).filter(DecisionSlotDB.id == slot.id).delete()
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id.in_(records)).delete(
        synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(records)).delete(
        synchronize_session=False)
    db.commit()


def test_a_frame_says_what_it_is(db, world):
    frame = build_frame(db, world["variant"].id)
    assert is_frame(frame)
    kinds = [m["kind"] for m in frame["modules"]]
    assert kinds == ["static", "content", "slot"]
    assert frame["envelope"] == {"subject": "Hello", "preheader": "Peek"}
    content = frame["modules"][1]
    assert content["content_version_id"] is not None, "the version used is recorded"
    assert content["variables"]["headline_medium"] == "Fixed headline"


def test_parity_with_the_live_send_render(db, world):
    """ADR-063: the frame path and the live path give the same output."""
    artifact, picks = render_frame(db, build_frame(db, world["variant"].id))
    assert artifact.body == render_variant_html(db, world["variant"].id, mode="send")
    assert [p["content_record_id"] for p in picks] == [world["picked"].id]


def test_edits_after_the_frame_do_not_reach_it(db, world):
    frame = build_frame(db, world["variant"].id)
    # Edit everything the frame copied: the header, and a newly published version.
    header = db.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.variant_id == world["variant"].id,
        ModuleInstanceDB.module_type == "header").one()
    header.module_data = {"subject": "Changed", "preheader": "Changed"}
    record = db.get(ContentRecordDB, world["fixed"].id)
    record.content = {"headline_medium": "Edited later", "body_medium": "x"}
    db.commit()
    create_content_version(db, content_record_id=record.id, created_by="test",
                           brand_id=world["brand"].id)

    artifact, _ = render_frame(db, frame)
    assert "Fixed headline" in artifact.body and "Edited later" not in artifact.body
    assert artifact.envelope["subject"] == "Hello"


def test_recorded_picks_survive_a_later_pick(db, world):
    frame = build_frame(db, world["variant"].id)
    _, picks = render_frame(db, frame)
    # The slot would now pick something else.
    db.add(DecisionResolutionDB(decision_slot_id=world["slot_id"], content_record_id=world["later"].id))
    db.commit()
    now_artifact, _ = render_frame(db, frame)
    replayed, _ = render_frame(db, frame, picks=picks)
    assert "Later pick" in now_artifact.body
    assert "Picked headline" in replayed.body and "Later pick" not in replayed.body


# --- stage 2: the send renders the frame and records what it sent -----------

@pytest.fixture
def sent(db, world, monkeypatch):
    """Snapshot the world, then edit it, then send to one consenting recipient.
    Returns what the provider was handed and the execution."""
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.delivery.providers import mock as mock_module
    from app.delivery.service import send_send_instance
    from app.recipients.consent import record_consent
    from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB
    from app.snapshots.db_models import SnapshotDB
    from app.snapshots.service import create_snapshot_for_variant

    brand = world["brand"]
    snapshot = create_snapshot_for_variant(db, world["variant"].id, brand_id=brand.id)
    # Edited after the snapshot: must not reach the recipient.
    record = db.get(ContentRecordDB, world["fixed"].id)
    record.content = {"headline_medium": "Edited after approval", "body_medium": "x"}
    db.commit()
    create_content_version(db, content_record_id=record.id, created_by="test", brand_id=brand.id)

    recipient = RecipientDB(external_id=f"frame-{uuid.uuid4()}", status="active")
    db.add(recipient); db.flush()
    db.add(AddressabilityDB(recipient_id=recipient.id, channel="email",
                            value={"email": f"{uuid.uuid4().hex[:8]}@example.invalid"},
                            status="active", is_primary=True))
    record_consent(db, recipient.id, "opted_in", brand.id, channel="email",
                   purpose="marketing", source="test", commit=False)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="frame send",
                          status="draft", provider="mock")
    db.add(send); db.flush()
    execution = DeliveryExecutionDB(send_instance_id=send.id, recipient_id=recipient.id,
                                    status="created", provider="mock", channel="email",
                                    purpose="marketing")
    db.add(execution); db.commit()

    captured = {}
    original = mock_module.MockProvider.send

    def capture(self, address, artifact):
        captured["artifact"] = artifact
        return original(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    send_send_instance(db, send.id, brand_id=brand.id)
    db.expire_all()
    yield {"artifact": captured["artifact"], "execution": db.get(DeliveryExecutionDB, execution.id),
           "snapshot_id": snapshot.id}

    db.rollback()
    from app.decision.service import execute_decision_slot  # noqa: F401
    db.query(DecisionResolutionDB).filter(DecisionResolutionDB.recipient_id == recipient.id).delete()
    db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id).delete()
    db.query(SendInstanceDB).filter(SendInstanceDB.id == send.id).delete()
    db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id == recipient.id).delete()
    db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id == recipient.id).delete()
    db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
    db.commit()


def test_the_send_delivers_the_frame_not_the_live_variant(sent):
    body = sent["artifact"].body
    assert "Fixed headline" in body and "Edited after approval" not in body, (
        "an edit made after the snapshot reached the recipient"
    )


def test_the_send_records_what_it_sent(sent):
    from app.rendering.frame import artifact_hash

    execution = sent["execution"]
    assert execution.status == "sent"
    assert execution.sent_at is not None
    assert execution.artifact_hash == artifact_hash(sent["artifact"])
    record = execution.delivery_record
    assert record["snapshot_id"] == sent["snapshot_id"]
    # The pick the send made for this recipient (their own resolution, made at
    # send time — personalisation), with the values that were in the message.
    [pick] = record["picks"]
    assert pick["decision_resolution_id"] is not None
    assert pick["variables"]["headline_medium"] in sent["artifact"].body


def test_a_frameless_snapshot_is_refused(db, world):
    from app.delivery.db_models import SendInstanceDB
    from app.delivery.service import send_send_instance
    from app.snapshots.db_models import SnapshotDB
    from app.snapshots.service import INLINE_LOCATION

    snapshot = SnapshotDB(variant_id=world["variant"].id, artifact_storage_type="inline",
                          artifact_location=INLINE_LOCATION, artifact_size=0, render_context={})
    db.add(snapshot); db.flush()
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=world["brand"].id, name="old",
                          status="draft", provider="mock")
    db.add(send); db.commit()
    try:
        with pytest.raises(ValueError, match="new snapshot"):
            send_send_instance(db, send.id, brand_id=world["brand"].id)
        db.refresh(send)
        assert send.status == "draft"
    finally:
        db.rollback()
        db.query(SendInstanceDB).filter(SendInstanceDB.id == send.id).delete()
        db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
        db.commit()


# --- stage 3: what a recipient got, rebuilt ----------------------------------

def _change_everything(db, world):
    """Everything a message depends on, changed after the send."""
    header = db.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.variant_id == world["variant"].id,
        ModuleInstanceDB.module_type == "header").one()
    header.module_data = {"subject": "Rewritten", "preheader": "Rewritten"}
    db.add(DecisionResolutionDB(decision_slot_id=world["slot_id"], content_record_id=world["later"].id))
    db.commit()
    for key in ("fixed", "picked"):
        record = db.get(ContentRecordDB, world[key].id)
        record.content = {"headline_medium": f"{key} rewritten", "body_medium": "x"}
        db.commit()
        create_content_version(db, content_record_id=record.id, created_by="test",
                               brand_id=world["brand"].id)


def test_the_message_is_rebuilt_exactly_after_everything_changed(db, world, sent):
    from app.delivery.service import reconstruct_delivery

    _change_everything(db, world)
    rebuilt = reconstruct_delivery(db, sent["execution"].id, brand_id=world["brand"].id)
    assert rebuilt["body"] == sent["artifact"].body
    assert rebuilt["envelope"]["subject"] == "Hello"
    assert rebuilt["hash_matches"] is True and rebuilt["templates_match"] is True
    assert rebuilt["sent_at"] == sent["execution"].sent_at
    kinds = {m["kind"] for m in rebuilt["modules"]}
    assert kinds == {"static", "content", "slot"}


def test_a_template_change_is_reported_not_hidden(db, world, sent, monkeypatch):
    import app.rendering.frame as frame_module
    from app.delivery.service import reconstruct_delivery

    monkeypatch.setattr(frame_module, "templates_fingerprint", lambda channel: "different")
    rebuilt = reconstruct_delivery(db, sent["execution"].id, brand_id=world["brand"].id)
    assert rebuilt["templates_match"] is False
    assert rebuilt["body"] == sent["artifact"].body, "the content is still exact"


def test_the_route_answers_for_the_brand_only(db, world, sent, foreign_api):
    from fastapi.testclient import TestClient

    from app.auth.permissions import VIEW
    from main import app
    from tests.machine import machine

    client = TestClient(app, raise_server_exceptions=False)
    path = f"/delivery/executions/{sent['execution'].id}/as-sent"
    with machine([VIEW]) as headers:
        ok = client.get(path, headers=headers)
    with foreign_api([VIEW]) as headers:
        foreign = client.get(path, headers=headers)
    assert ok.status_code == 200, ok.text
    assert ok.json()["body"] == sent["artifact"].body and ok.json()["hash_matches"] is True
    assert foreign.status_code == 404


def test_an_unsent_execution_has_nothing_to_rebuild(db, world, sent):
    from app.delivery.service import reconstruct_delivery

    execution = sent["execution"]
    execution.status, execution.delivery_record = "created", None
    db.commit()
    with pytest.raises(ValueError, match="no delivery record"):
        reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)


def test_without_a_subject_the_rebuild_uses_the_sends_fallback(db, world, sent):
    """The send falls back to the send's name when the frame has no subject;
    the rebuild must apply the same rule, or its hash can never match."""
    from app.delivery.db_models import SendInstanceDB
    from app.delivery.service import reconstruct_delivery
    from app.rendering.frame import artifact_hash, render_frame
    from app.snapshots.db_models import SnapshotDB

    execution = sent["execution"]
    snapshot = db.get(SnapshotDB, sent["snapshot_id"])
    snapshot.render_context = {**snapshot.render_context, "envelope": {}}
    db.commit()
    send_name = db.get(SendInstanceDB, execution.send_instance_id).name
    expected, _ = render_frame(db, snapshot.render_context, picks=execution.delivery_record["picks"])
    expected.envelope["subject"] = send_name
    execution.artifact_hash = artifact_hash(expected)
    db.commit()

    rebuilt = reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)
    assert rebuilt["envelope"]["subject"] == send_name
    assert rebuilt["hash_matches"] is True


# --- stage 4: no HTML on disk; previews are the frame laid out ---------------

def test_a_snapshot_writes_nothing_to_disk_and_previews_from_its_frame(db, world):
    from pathlib import Path

    from fastapi.testclient import TestClient

    from app.auth.permissions import VIEW
    from app.snapshots.db_models import SnapshotDB
    from app.snapshots.service import create_snapshot_for_variant
    from main import app
    from tests.machine import machine

    storage = Path(__file__).resolve().parents[2] / "storage" / "snapshots"
    before = set(storage.glob("*")) if storage.exists() else set()
    snapshot = create_snapshot_for_variant(db, world["variant"].id, brand_id=world["brand"].id)
    try:
        after = set(storage.glob("*")) if storage.exists() else set()
        assert after == before, f"a snapshot wrote files: {after - before}"
        client = TestClient(app, raise_server_exceptions=False)
        with machine([VIEW]) as headers:
            page = client.get(f"/snapshots/{snapshot.id}/html", headers=headers)
        assert page.status_code == 200, page.text[:200]
        expected, _ = render_frame(db, db.get(SnapshotDB, snapshot.id).render_context)
        assert page.text == expected.body
    finally:
        db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
        db.commit()


def test_a_frameless_snapshot_says_why_it_has_no_preview(db, world):
    from fastapi.testclient import TestClient

    from app.auth.permissions import VIEW
    from app.snapshots.db_models import SnapshotDB
    from app.snapshots.service import INLINE_LOCATION
    from main import app
    from tests.machine import machine

    snapshot = SnapshotDB(variant_id=world["variant"].id, artifact_storage_type="file",
                          artifact_location="/tmp/old.html", artifact_size=0, render_context={})
    db.add(snapshot); db.commit()
    try:
        client = TestClient(app, raise_server_exceptions=False)
        with machine([VIEW]) as headers:
            page = client.get(f"/snapshots/{snapshot.id}/html", headers=headers)
        assert page.status_code == 404
        assert "new snapshot" in page.json()["detail"]
    finally:
        db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
        db.commit()
