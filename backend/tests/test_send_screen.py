"""What the React send screen needs from the API (task-67; ADR-183 addendum
2026-10-12).

Decided with the user 2026-10-12, one question at a time:
  - one guided screen per variant: freeze, plan, test, confirm and send;
  - approval unchanged: a person who may fire is the approval (ADR-174);
  - the test renders the FROZEN snapshot as a chosen recipient, its own
    subject marked "[Test] ", through the planned send's provider; still no
    delivery, no unsubscribe link, no tracking (ADR-191);
  - the confirmation shows the recipients as of now, not as planned.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import SENDS_PLAN, VIEW
from app.campaigns.db_models import ModuleInstanceDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.settings.service import get_max_send_recipients
from app.snapshots.service import create_snapshot_for_variant
from main import app
from tests import test_render_skip as fixtures
from tests.machine import machine
from tests.test_api_guard import signed_in

api = TestClient(app, raise_server_exceptions=False)
db = fixtures.db
world = fixtures.world


@pytest.fixture
def planned(db, world):
    """A frozen static email, planned as a mock send to `people`."""
    def make(channel="email", people=()):
        brand = world["brand"]
        variant = world["variant"](channel, static=channel == "email", slots=0 if channel == "email" else 1)
        snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
        world["made"]["snapshots"].append(snapshot.id)
        send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name=f"screen-{uuid.uuid4().hex[:6]}",
                              status="draft", provider="mock")
        db.add(send)
        db.flush()
        world["made"]["sends"].append(send.id)
        for person in people:
            db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status="created",
                                       provider="mock", channel=channel, purpose="marketing"))
        db.commit()
        return variant, send
    return make


@pytest.fixture
def mailed(monkeypatch):
    """What the mock provider was handed: (address, artifact)."""
    seen = []
    original = mock_module.MockProvider.send

    def capture(self, address, artifact):
        seen.append((address, artifact))
        return original(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    return seen


def _test(cookied, csrf, variant_id, **body):
    return cookied.post(f"/delivery/variants/{variant_id}/test",
                        json={"to": "test@example.invalid", "provider": "mock", **body},
                        headers={"X-CSRF-Token": csrf})


def _snapshots(db, variant_id):
    from app.snapshots.db_models import SnapshotDB

    db.expire_all()
    return db.query(SnapshotDB).filter(SnapshotDB.variant_id == variant_id).count()


# --- what goes out, before anything is frozen (ADR-183 addendum 2026-10-13) -------------------

def test_the_preview_is_the_email_as_it_would_be_frozen_and_stores_nothing(db, world):
    variant = world["variant"]("email", static=True, slots=0)
    with signed_in(db) as (cookied, _token, _csrf):
        response = cookied.get(f"/snapshots/variants/{variant.id}/preview")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["channel"] == "email" and body["subject"] == "Hello"
    assert "Go" in body["html"]
    assert _snapshots(db, variant.id) == 0, "a preview freezes nothing"


def test_the_preview_of_another_brands_variant_is_not_found(db, world, foreign_brand):
    variant = world["variant"]("email", static=True, slots=0)
    from app.campaigns.db_models import CampaignDB

    campaign = db.get(CampaignDB, variant.campaign_id)
    campaign.brand_id = foreign_brand.id
    db.commit()
    try:
        with signed_in(db) as (cookied, _token, _csrf):
            assert cookied.get(f"/snapshots/variants/{variant.id}/preview").status_code == 404
    finally:
        campaign.brand_id = world["brand"].id
        db.commit()


# --- the test: any time, nothing stored ----------------------------------------------------------

def test_a_test_is_the_email_as_it_would_be_frozen_with_its_own_subject(db, world, mailed):
    variant = world["variant"]("email", static=True, slots=0)
    with signed_in(db) as (cookied, _token, csrf):
        response = _test(cookied, csrf, variant.id)
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    [(address, artifact)] = mailed
    assert address == "test@example.invalid"
    assert artifact.envelope["subject"] == "[Test] Hello"
    assert "Go" in artifact.body
    assert _snapshots(db, variant.id) == 0, "a test freezes nothing"


def test_a_test_is_not_a_delivery(db, world, mailed):
    person = world["person"]()
    variant = world["variant"]("email", static=True, slots=0)
    with signed_in(db) as (cookied, _token, csrf):
        _test(cookied, csrf, variant.id, recipient_id=person.id)
    [(_address, artifact)] = mailed
    assert "/unsubscribe/" not in artifact.body, "a test has no token, so no link"
    assert "list_unsubscribe" not in artifact.envelope
    from app.brand_profiles.service import default_profile

    wording = (default_profile(db, world["brand"].id).field_values or {}).get("unsubscribe_text")
    assert wording and wording in artifact.body, "the wording still shows, unlinked (ADR-194)"
    db.expire_all()
    assert db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.recipient_id == person.id).count() == 0


def test_a_push_cannot_be_tested_by_email(db, world, mailed):
    variant = world["variant"]("push", static=False, slots=1)
    with signed_in(db) as (cookied, _token, csrf):
        response = _test(cookied, csrf, variant.id)
    assert response.status_code == 409 and "push" in response.json()["detail"]
    assert mailed == []


def test_testing_needs_the_right_to_send(db, world):
    variant = world["variant"]("email", static=True, slots=0)
    with machine([VIEW, SENDS_PLAN]) as headers:
        response = api.post(f"/delivery/variants/{variant.id}/test",
                            json={"to": "x@example.invalid", "provider": "mock"}, headers=headers)
    assert response.status_code == 403


# --- planning freezes, and only planning -------------------------------------------------------

def _group_of(db, world, people):
    from app.audience.service import add_member, create_group

    group = create_group(db, f"screen-{uuid.uuid4().hex[:6]}", brand_id=world["brand"].id)
    world["made"]["groups"].append(group.id)
    for person in people:
        add_member(db, group.id, person.id, brand_id=world["brand"].id)
    return group


def _plan(cookied, csrf, variant_id, group_id, **extra):
    return cookied.post(f"/delivery/variants/{variant_id}/send-instances",
                        json={"name": "Screen send", "audience_group_id": group_id, "provider": "mock", **extra},
                        headers={"X-CSRF-Token": csrf})


def test_planning_freezes_the_variant_and_plans_the_send_in_one_go(db, world):
    people = [world["person"]() for _ in range(2)]
    variant = world["variant"]("email", static=True, slots=0)
    group = _group_of(db, world, people)
    with signed_in(db) as (cookied, _token, csrf):
        response = _plan(cookied, csrf, variant.id, group.id)
    assert response.status_code == 201, response.text
    send = db.get(SendInstanceDB, response.json()["id"])
    world["made"]["sends"].append(send.id)
    world["made"]["snapshots"].append(send.snapshot_id)
    assert _snapshots(db, variant.id) == 1
    from app.snapshots.db_models import SnapshotDB

    assert db.get(SnapshotDB, send.snapshot_id).variant_id == variant.id
    assert send.status == "draft"


def test_a_refused_plan_leaves_no_snapshot_behind(db, world):
    variant = world["variant"]("email", static=True, slots=0)
    empty = _group_of(db, world, [])
    with signed_in(db) as (cookied, _token, csrf):
        response = _plan(cookied, csrf, variant.id, empty.id)
    assert response.status_code == 409, response.text
    assert _snapshots(db, variant.id) == 0


def test_another_brands_group_is_not_found_and_leaves_nothing(db, world, foreign_brand):
    from app.audience.service import create_group

    variant = world["variant"]("email", static=True, slots=0)
    foreign = create_group(db, f"screen-f-{uuid.uuid4().hex[:6]}", brand_id=foreign_brand.id)
    world["made"]["groups"].append(foreign.id)
    with signed_in(db) as (cookied, _token, csrf):
        response = _plan(cookied, csrf, variant.id, foreign.id)
    assert response.status_code == 404
    assert _snapshots(db, variant.id) == 0


def test_the_open_sends_of_a_variant_can_be_listed(db, world, planned):
    variant, send = planned()
    _other_variant, other = planned()
    with signed_in(db) as (cookied, _token, _csrf):
        listed = cookied.get(f"/delivery/send-instances?variant_id={variant.id}").json()["items"]
    ids = [s["id"] for s in listed]
    assert send.id in ids and other.id not in ids


# --- the confirmation --------------------------------------------------------------------

def test_the_confirmation_counts_as_of_now(db, world, planned):
    people = [world["person"]() for _ in range(3)]
    _variant, send = planned(people=people)
    db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id,
                                         DeliveryExecutionDB.recipient_id == people[0].id).update({"status": "sent"})
    db.commit()
    with signed_in(db) as (cookied, _token, _csrf):
        response = cookied.get(f"/delivery/send-instances/{send.id}/recipients-now")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recipients"] == 2, "who is still to be mailed, as the send counts them"
    assert body["cap"] == get_max_send_recipients(db)
    assert body["provider"] == "mock" and body["reaches_real_inboxes"] is False
    assert body["status"] == "draft"


def test_the_confirmation_is_brand_scoped(db, world, planned, foreign_brand):
    _variant, send = planned()
    send.brand_id = foreign_brand.id
    db.commit()
    try:
        with signed_in(db) as (cookied, _token, _csrf):
            response = cookied.get(f"/delivery/send-instances/{send.id}/recipients-now")
        assert response.status_code == 404
    finally:
        send.brand_id = world["brand"].id
        db.commit()


# --- freezing ---------------------------------------------------------------------------

def test_freezing_a_variant_that_does_not_exist_is_a_404(db):
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.post("/snapshots/variants/987654321", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 404


# --- what the screen offers ----------------------------------------------------------------

def test_the_provider_list_says_who_needs_a_sender(db):
    with signed_in(db) as (cookied, _token, _csrf):
        providers = {p["name"]: p for p in cookied.get("/settings").json()["delivery_providers"]}
    assert providers["mock"]["needs_from_address"] is False and providers["mock"]["default_from_address"] is None
    assert providers["resend"]["needs_from_address"] is True and providers["resend"]["default_from_address"]


def test_a_sends_detail_names_its_campaign_and_variant(db, world, planned):
    variant, send = planned()
    with signed_in(db) as (cookied, _token, _csrf):
        detail = cookied.get(f"/delivery/send-instances/{send.id}").json()
    assert (detail["campaign_id"], detail["variant_id"]) == (variant.campaign_id, variant.id)
