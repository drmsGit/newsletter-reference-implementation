"""A recipient for whom nothing meaningful rendered is not sent to (task-228).

ADR-086 said the email must not be sent when no meaningful content remains;
its 2026-10-08 addendum, decided with the user, defines that per recipient,
after rendering, in two tiers:

  - **the floor, always:** nothing but the envelope rendered (email: only the
    header's subject and preheader; push: an empty notification) → skipped,
    "render: nothing to show — no module produced content for this person";
  - **the option, per send, off by default:** "Don't send if no slot
    resolved" → a recipient whose slots all came up empty is skipped even
    though static content rendered, "render: no personalised block found
    anything for this person". A variant with no slots is never skipped by it.

Both are `excluded` under the stage `render`, beside the exclusion stack's
reasons, so "why didn't this person get it" has one place to look.

Slots here resolve through a stub of `execute_decision_slot`: a recipient in
`resolves` gets a pick, anyone else finds nothing — the per-recipient case.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import (
    create_campaign, create_decision_slot_for_variant, create_module_for_variant, set_envelope_fields,
)
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.content.service import create_content, create_content_version
from app.database import SessionLocal
from app.delivery import exclusion
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.delivery.service import prepare_send_from_audience, send_instance_detail, send_send_instance
from app.recipients.consent import record_consent
from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB
from app.snapshots.db_models import SnapshotDB
from app.snapshots.service import create_snapshot_for_variant

TAG = f"rs{uuid.uuid4().hex[:6]}"
NOTHING = "render: nothing to show — no module produced content for this person"
NO_PICK = "render: no personalised block found anything for this person"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db, monkeypatch):
    """Builds variants, sends them, and cleans up whatever was made."""
    brand = ensure_default_brand(db)
    made = {"campaigns": [], "records": [], "slots": [], "snapshots": [], "sends": [], "people": [], "groups": []}
    resolves: set[int] = set()
    delivered: list[int] = []

    record = create_content(db, title=f"{TAG}-pick", brand_id=brand.id, content={
        "headline_medium": "Picked for you", "body_medium": "Body", "button_label": "Read",
        "button_url": "https://example.com/story", "push_title": "Picked", "push_body": "For you"})
    create_content_version(db, content_record_id=record.id, created_by="test", brand_id=brand.id)
    made["records"].append(record.id)

    def fake_execute(db_, slot_id, recipient_id=None, **_):
        if recipient_id not in resolves:
            raise ValueError("nothing to pick")
        resolution = DecisionResolutionDB(decision_slot_id=slot_id, recipient_id=recipient_id,
                                          content_record_id=record.id)
        db_.add(resolution)
        db_.commit()
        # Like the real one: the resolution it made. A send treats None as
        # "found nothing now" (task-320).
        return resolution

    monkeypatch.setattr("app.decision.service.execute_decision_slot", fake_execute)
    original = mock_module.MockProvider.send

    def capture(self, address, artifact):
        delivered.append(address)
        return original(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", capture)

    def variant(channel="email", *, static=False, slots=1):
        campaign = create_campaign(db, name=f"{TAG}-{uuid.uuid4().hex[:4]}", brand_id=brand.id, channel=channel)
        made["campaigns"].append(campaign.id)
        v = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
        if channel == "email":
            set_envelope_fields(db, v.id, {"subject": "Hello", "preheader": "Peek"}, brand_id=brand.id)
        if static:
            create_module_for_variant(db, variant_id=v.id, module_type="cta",
                                      module_data={"label": "Go", "url": "https://example.com"}, brand_id=brand.id)
        for _ in range(slots):
            slot = create_decision_slot_for_variant(db, variant_id=v.id, name=f"{TAG}-slot", brand_id=brand.id)
            made["slots"].append(slot.id)
            create_module_for_variant(db, variant_id=v.id, module_type="single_stack" if channel == "email" else "notification",
                                      decision_slot_id=slot.id, brand_id=brand.id)
        db.commit()
        return v

    def person(channel="email", *, picks=False):
        r = RecipientDB(external_id=f"{TAG}-{uuid.uuid4().hex[:6]}", status="active")
        db.add(r); db.flush()
        value = {"email": f"{uuid.uuid4().hex[:8]}@example.invalid"} if channel == "email" else {"token": uuid.uuid4().hex}
        db.add(AddressabilityDB(recipient_id=r.id, channel=channel, value=value, status="active", is_primary=True))
        record_consent(db, r.id, "opted_in", brand.id, channel=channel, purpose="marketing", source="test", commit=False)
        db.commit()
        made["people"].append(r.id)
        if picks:
            resolves.add(r.id)
        return r

    def send(v, people, *, skip=False):
        snapshot = create_snapshot_for_variant(db, v.id, brand_id=brand.id)
        made["snapshots"].append(snapshot.id)
        s = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name=f"{TAG}-send", status="draft",
                           provider="mock", skip_without_resolution=skip)
        db.add(s); db.flush()
        made["sends"].append(s.id)
        for p in people:
            db.add(DeliveryExecutionDB(send_instance_id=s.id, recipient_id=p.id, status="created", provider="mock",
                                       channel=v.channel, purpose="marketing"))
        db.commit()
        delivered.clear()
        send_send_instance(db, s.id, brand_id=brand.id)
        db.expire_all()
        rows = db.query(DeliveryExecutionDB).filter_by(send_instance_id=s.id).all()
        return s, {r.recipient_id: (r.status, r.exclusion_reason) for r in rows}

    yield {"variant": variant, "person": person, "send": send, "brand": brand, "delivered": delivered, "made": made}

    db.rollback()
    made["sends"] += [i for (i,) in db.query(SendInstanceDB.id).filter(SendInstanceDB.audience_group_id.in_(made["groups"]))]
    db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id.in_(made["slots"])).delete(synchronize_session=False)
    db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id.in_(made["sends"])).delete(synchronize_session=False)
    db.query(SendInstanceDB).filter(SendInstanceDB.id.in_(made["sends"])).delete(synchronize_session=False)
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id.in_(made["groups"])).delete(synchronize_session=False)
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id.in_(made["groups"])).delete(synchronize_session=False)
    db.query(SnapshotDB).filter(SnapshotDB.id.in_(made["snapshots"])).delete(synchronize_session=False)
    variants = [v for (v,) in db.query(VariantDB.id).filter(VariantDB.campaign_id.in_(made["campaigns"]))]
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variants)).delete(synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.id.in_(made["slots"])).delete(synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(variants)).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id.in_(made["campaigns"])).delete(synchronize_session=False)
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id.in_(made["records"])).delete(synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(made["records"])).delete(synchronize_session=False)
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(made["people"])).delete(synchronize_session=False)
    db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id.in_(made["people"])).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(made["people"])).delete(synchronize_session=False)
    db.commit()


class TestTheFloor:
    def test_an_email_with_only_its_header_left_is_not_sent(self, world):
        anna = world["person"]()
        _, rows = world["send"](world["variant"](), [anna])
        assert rows[anna.id] == ("excluded", NOTHING)
        assert world["delivered"] == []

    def test_a_push_with_nothing_resolved_is_not_sent_blank(self, world):
        """The push renderer's own comment said the send must refuse this; nothing did."""
        ben = world["person"]("push")
        _, rows = world["send"](world["variant"]("push"), [ben])
        assert rows[ben.id] == ("excluded", NOTHING)
        assert world["delivered"] == []

    def test_the_floor_holds_with_the_option_off_and_per_recipient(self, world):
        anna, ben = world["person"](picks=True), world["person"]()
        _, rows = world["send"](world["variant"](), [anna, ben], skip=False)
        assert rows[anna.id] == ("sent", None)
        assert rows[ben.id] == ("excluded", NOTHING), "the send goes on for others; this one is skipped"

    def test_static_content_alone_is_meaningful(self, world):
        anna = world["person"]()
        _, rows = world["send"](world["variant"](static=True, slots=0), [anna])
        assert rows[anna.id] == ("sent", None)


class TestTheOption:
    def test_off_static_content_with_empty_slots_ships(self, world):
        """Case 2: the personalised block was a bonus."""
        anna = world["person"]()
        _, rows = world["send"](world["variant"](static=True), [anna], skip=False)
        assert rows[anna.id] == ("sent", None)

    def test_on_a_recipient_whose_slots_all_came_up_empty_is_skipped(self, world):
        """Case 3: the slots were the point."""
        anna, ben = world["person"](picks=True), world["person"]()
        _, rows = world["send"](world["variant"](static=True, slots=2), [anna, ben], skip=True)
        assert rows[anna.id] == ("sent", None)
        assert rows[ben.id] == ("excluded", NO_PICK)

    def test_on_a_variant_with_no_slots_always_ships(self, world):
        """Case 1: a focused email has nothing to resolve."""
        anna = world["person"]()
        _, rows = world["send"](world["variant"](static=True, slots=0), [anna], skip=True)
        assert rows[anna.id] == ("sent", None)

    def test_on_the_floor_still_names_its_own_reason(self, world):
        anna = world["person"]()
        _, rows = world["send"](world["variant"](), [anna], skip=True)
        assert rows[anna.id] == ("excluded", NOTHING), "nothing rendered is the floor's fact, not the option's"


def test_the_sends_detail_counts_them_under_render(db, world):
    anna, ben, cleo = world["person"](picks=True), world["person"](), world["person"]()
    s, _ = world["send"](world["variant"](static=True), [anna, ben, cleo], skip=True)
    detail = send_instance_detail(db, s.id, brand_id=world["brand"].id)
    assert detail.exclusions_by_stage == {exclusion.STAGE_RENDER: 2}
    row = db.get(SendInstanceDB, s.id)
    assert (row.sent_count, row.excluded_count) == (1, 2)


class TestPlanning:
    def _group(self, db, world, *people):
        group = AudienceGroupDB(brand_id=world["brand"].id, name=f"{TAG}-{uuid.uuid4().hex[:4]}")
        db.add(group); db.flush()
        world["made"]["groups"].append(group.id)
        for p in people:
            db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=p.id))
        db.commit()
        return group

    def test_the_option_is_off_unless_asked_for(self, db, world):
        v = world["variant"](static=True)
        snapshot = create_snapshot_for_variant(db, v.id, brand_id=world["brand"].id)
        world["made"]["snapshots"].append(snapshot.id)
        group = self._group(db, world, world["person"]())
        plain = prepare_send_from_audience(db, snapshot.id, "plain", group.id, "mock", brand_id=world["brand"].id)
        asked = prepare_send_from_audience(db, snapshot.id, "asked", group.id, "mock", brand_id=world["brand"].id,
                                           skip_without_resolution=True)
        world["made"]["sends"] += [plain.id, asked.id]
        assert (plain.skip_without_resolution, asked.skip_without_resolution) == (False, True)

    def test_the_json_route_and_the_plan_form_carry_it(self, db, world, person_client):
        client, csrf = person_client
        v = world["variant"](static=True)
        snapshot = create_snapshot_for_variant(db, v.id, brand_id=world["brand"].id)
        world["made"]["snapshots"].append(snapshot.id)
        group = self._group(db, world, world["person"]())
        response = client.post(f"/delivery/snapshots/{snapshot.id}/send-instances", headers=csrf, json={
            "name": "json", "audience_group_id": group.id, "provider": "mock", "skip_without_resolution": True})
        assert response.status_code == 201, response.text
        world["made"]["sends"].append(response.json()["id"])
        assert response.json()["skip_without_resolution"] is True

        campaign_id = db.get(VariantDB, v.id).campaign_id
        client.post(f"/ui/campaigns/{campaign_id}/snapshots/{snapshot.id}/send-instances", headers=csrf, data={
            "csrf_token": csrf["X-CSRF-Token"], "name": f"{TAG}-form", "audience_group_id": group.id,
            "provider": "mock", "skip_without_resolution": "on"}, follow_redirects=False)
        form = db.query(SendInstanceDB).filter_by(snapshot_id=snapshot.id, name=f"{TAG}-form").one()
        world["made"]["sends"].append(form.id)
        assert form.skip_without_resolution is True


@pytest.fixture
def person_client(db, default_brand):
    from sqlalchemy import text

    from app.auth import service as auth
    from main import app

    user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid", role_key="admin",
                            brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, {"X-CSRF-Token": auth.csrf_token_for(token)}
    db.rollback()
    db.execute(text("DELETE FROM audit_events WHERE actor_id = :u AND actor_type = 'user'"), {"u": user.id})
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()
