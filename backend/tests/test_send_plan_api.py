"""`POST /delivery/snapshots/{id}/send-instances` — planning a send as JSON
(task-49, gap C8).

Until now `prepare_send_from_audience` had one call site, the Jinja form, so a
client of the JSON API could list sends but never create one. This is the twin
of that form. It plans — resolves the audience to executions — and sends
nothing; firing stays the separate, `sends.execute` call.

The cross-brand tests use `foreign_api`, not the default brand: a fallback to
the default brand would satisfy a test written against it (conftest, "the rule
they exist to make easy").
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.auth.permissions import SENDS_PLAN, VIEW
from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, VariantDB
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.recipients.consent import record_consent
from app.recipients.db_models import AddressabilityDB, RecipientDB
from app.snapshots.db_models import SnapshotDB
from app.snapshots.service import INLINE_LOCATION
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db):
    """A snapshot and an audience group (one consenting recipient) in the
    default brand, all removed afterwards, plus the ids of any send a test
    planned."""
    brand = ensure_default_brand(db)
    campaign = CampaignDB(brand_id=brand.id, name=f"planapi-{uuid.uuid4().hex[:8]}")
    db.add(campaign)
    db.flush()
    variant = VariantDB(
        campaign_id=campaign.id, channel="email", name="planapi", status="draft",
    )
    db.add(variant)
    db.flush()
    snapshot = SnapshotDB(
        variant_id=variant.id, artifact_storage_type="inline",
        artifact_location=INLINE_LOCATION, artifact_size=0, render_context={},
    )
    db.add(snapshot)
    recipient = RecipientDB(external_id=f"planapi-{uuid.uuid4()}", status="active")
    db.add(recipient)
    db.flush()
    db.add(AddressabilityDB(
        recipient_id=recipient.id, channel="email",
        value={"email": f"{uuid.uuid4()}@example.invalid"},
        status="active", is_primary=True,
    ))
    record_consent(db, recipient.id, "opted_in", brand.id, source="test",
                   note="planapi", commit=False)
    group = AudienceGroupDB(brand_id=brand.id, name=f"planapi-{uuid.uuid4().hex[:8]}")
    db.add(group)
    db.flush()
    empty_group = AudienceGroupDB(brand_id=brand.id, name=f"planapi-empty-{uuid.uuid4().hex[:8]}")
    db.add(empty_group)
    db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=recipient.id))
    db.commit()

    state = {
        "snapshot_id": snapshot.id, "group_id": group.id,
        "empty_group_id": empty_group.id, "sends": [],
    }
    yield state

    db.rollback()
    from sqlalchemy import text

    for send_id in state["sends"]:
        db.query(DeliveryExecutionDB).filter(
            DeliveryExecutionDB.send_instance_id == send_id).delete()
        db.query(SendInstanceDB).filter(SendInstanceDB.id == send_id).delete()
    db.execute(text("DELETE FROM consent_events WHERE recipient_id = :r"), {"r": recipient.id})
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group.id).delete()
    db.query(AudienceGroupDB).filter(
        AudienceGroupDB.id.in_([group.id, empty_group.id])).delete(synchronize_session=False)
    db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id == recipient.id).delete()
    db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
    db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.commit()


def _plan(headers, world, snapshot_id=None, group_id=None, **extra):
    response = client.post(
        f"/delivery/snapshots/{snapshot_id or world['snapshot_id']}/send-instances",
        json={"name": "planapi send", "audience_group_id": group_id or world["group_id"], **extra},
        headers=headers,
    )
    if response.status_code == 201:
        world["sends"].append(response.json()["id"])
    return response


def test_planning_creates_a_draft_with_one_execution_per_recipient(world, db):
    with machine([VIEW, SENDS_PLAN]) as headers:
        response = _plan(headers, world, from_address="  news@example.invalid ")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["snapshot_id"] == world["snapshot_id"]
    assert body["audience_group_id"] == world["group_id"]
    assert body["from_address"] == "news@example.invalid"
    executions = db.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.send_instance_id == body["id"]).all()
    assert [e.status for e in executions] == ["created"]


def test_planning_sends_nothing(world, db):
    with machine([VIEW, SENDS_PLAN]) as headers:
        body = _plan(headers, world).json()

    db.expire_all()
    row = db.get(SendInstanceDB, body["id"])
    assert row.status == "draft" and row.sent_count == 0


def test_a_scheduled_time_makes_it_scheduled(world):
    when = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    with machine([VIEW, SENDS_PLAN]) as headers:
        response = _plan(headers, world, scheduled_at=when.isoformat())

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "scheduled"
    assert response.json()["scheduled_at"] is not None


def test_an_audience_with_nobody_in_it_is_refused(world):
    with machine([VIEW, SENDS_PLAN]) as headers:
        response = _plan(headers, world, group_id=world["empty_group_id"])

    assert response.status_code == 409, response.text
    assert "0 consenting recipients" in response.json()["detail"]


def test_the_send_cap_is_enforced(world, monkeypatch):
    # The service imports the getter inside the function, so it is looked up
    # on the settings module at call time — patch it there.
    import app.settings.service as settings

    monkeypatch.setattr(settings, "get_max_send_recipients", lambda db: 0)
    with machine([VIEW, SENDS_PLAN]) as headers:
        response = _plan(headers, world)

    assert response.status_code == 409, response.text
    assert "send cap" in response.json()["detail"]


def test_another_brands_snapshot_is_not_found(world, foreign_api):
    with foreign_api([VIEW, SENDS_PLAN]) as headers:
        response = _plan(headers, world)

    assert response.status_code == 404, response.text
    assert "Snapshot" in response.json()["detail"]


def test_another_brands_audience_is_not_found(world, foreign_brand, foreign_api, db):
    """Snapshot in the caller's brand, audience in the default brand: the
    snapshot check cannot be what refuses it, so this isolates the audience
    boundary. A snapshot of the foreign brand is made for the purpose."""
    from app.campaigns.db_models import CampaignDB, VariantDB

    campaign = CampaignDB(brand_id=foreign_brand.id, name=f"planapi-f-{uuid.uuid4().hex[:6]}")
    db.add(campaign)
    db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="f", status="draft")
    db.add(variant)
    db.flush()
    snapshot = SnapshotDB(
        variant_id=variant.id, artifact_storage_type="inline",
        artifact_location=INLINE_LOCATION, artifact_size=0, render_context={},
    )
    db.add(snapshot)
    db.commit()
    try:
        with foreign_api([VIEW, SENDS_PLAN]) as headers:
            response = _plan(headers, world, snapshot_id=snapshot.id)
    finally:
        db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
        db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
        db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
        db.commit()

    assert response.status_code == 404, response.text
    assert "Audience group" in response.json()["detail"]


def test_a_reader_cannot_plan(world, db):
    before = db.query(SendInstanceDB).count()
    with machine([VIEW]) as headers:
        response = _plan(headers, world)

    assert response.status_code == 403, response.text
    db.expire_all()
    assert db.query(SendInstanceDB).count() == before


def test_planning_needs_plan_not_execute(world):
    """The point of the permission split (ADR-166): a credential that may plan
    a send is not thereby one that may mail people."""
    from app.auth.permissions import SENDS_EXECUTE

    with machine([VIEW, SENDS_PLAN]) as headers:
        planned = _plan(headers, world)
        fired = client.post(
            f"/delivery/send-instances/{planned.json()['id']}/send", headers=headers)

    assert planned.status_code == 201
    assert fired.status_code == 403, fired.text


def test_a_session_without_a_csrf_token_is_refused(world, db):
    from app.auth import service as auth
    from tests.test_api_guard import signed_in

    with signed_in(db) as (cookied, _token, csrf):
        refused = cookied.post(
            f"/delivery/snapshots/{world['snapshot_id']}/send-instances",
            json={"name": "x", "audience_group_id": world["group_id"]},
        )
        allowed = cookied.post(
            f"/delivery/snapshots/{world['snapshot_id']}/send-instances",
            json={"name": "x", "audience_group_id": world["group_id"]},
            headers={"X-CSRF-Token": csrf},
        )
        if allowed.status_code == 201:
            world["sends"].append(allowed.json()["id"])

    assert refused.status_code == 403, refused.text
    assert allowed.status_code == 201, allowed.text


def test_a_provider_that_cannot_carry_the_channel_is_refused_at_plan_time(world, db):
    """Not at fire time, after the send was reviewed and scheduled."""
    before = db.query(SendInstanceDB).count()
    with machine([VIEW, SENDS_PLAN]) as headers:
        unknown = _plan(headers, world, provider="carrier-pigeon")
    assert unknown.status_code == 409, unknown.text
    assert "mock" in unknown.json()["detail"], "the refusal should say what is offered"
    db.expire_all()
    assert db.query(SendInstanceDB).count() == before


def test_a_name_too_long_for_the_column_is_422_not_500(world):
    with machine([VIEW, SENDS_PLAN]) as headers:
        response = client.post(
            f"/delivery/snapshots/{world['snapshot_id']}/send-instances",
            json={"name": "x" * 256, "audience_group_id": world["group_id"]},
            headers=headers,
        )
    assert response.status_code == 422, response.text


def test_resend_cannot_be_planned_for_a_push_variant(world, db):
    """The case `providers_for_channel` was written for: the form stopped
    offering it, and the JSON route must refuse it rather than rely on that."""
    variant = db.get(VariantDB, db.get(SnapshotDB, world["snapshot_id"]).variant_id)
    push = VariantDB(campaign_id=variant.campaign_id, channel="push", name="push", status="draft")
    db.add(push)
    db.flush()
    snapshot = SnapshotDB(
        variant_id=push.id, artifact_storage_type="inline",
        artifact_location=INLINE_LOCATION, artifact_size=0, render_context={},
    )
    db.add(snapshot)
    db.commit()
    try:
        with machine([VIEW, SENDS_PLAN]) as headers:
            response = _plan(headers, world, snapshot_id=snapshot.id, provider="resend")
        assert response.status_code == 409, response.text
        assert "push" in response.json()["detail"]
    finally:
        db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
        db.query(VariantDB).filter(VariantDB.id == push.id).delete()
        db.commit()
