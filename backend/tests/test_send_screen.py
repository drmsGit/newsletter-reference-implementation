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


def _test(cookied, csrf, send_id, **body):
    return cookied.post(f"/delivery/send-instances/{send_id}/test", json={"to": "test@example.invalid", **body},
                        headers={"X-CSRF-Token": csrf})


# --- the test send ----------------------------------------------------------------------

def test_the_test_is_the_frozen_email_with_its_own_subject(db, world, planned, mailed):
    variant, send = planned()
    # Edited after freezing: the test must not show it.
    module = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id,
                                               ModuleInstanceDB.module_type == "cta").one()
    module.module_data = {"label": "Changed after freezing", "url": "https://example.com"}
    db.commit()
    with signed_in(db) as (cookied, _token, csrf):
        response = _test(cookied, csrf, send.id)
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    [(address, artifact)] = mailed
    assert address == "test@example.invalid"
    assert artifact.envelope["subject"] == "[Test] Hello"
    assert "Changed after freezing" not in artifact.body and "Go" in artifact.body


def test_a_test_is_not_a_delivery(db, world, planned, mailed):
    person = world["person"]()
    _variant, send = planned(people=[person])
    before = db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id).count()
    with signed_in(db) as (cookied, _token, csrf):
        _test(cookied, csrf, send.id, recipient_id=person.id)
    [(_address, artifact)] = mailed
    assert "/unsubscribe/" not in artifact.body, "a test has no token, so no link"
    from app.snapshots.db_models import SnapshotDB

    wording = db.get(SnapshotDB, send.snapshot_id).render_context["brand_profile"]["values"].get("unsubscribe_text")
    assert wording and wording in artifact.body, "the wording still shows, unlinked (ADR-194)"
    assert "list_unsubscribe" not in artifact.envelope
    db.expire_all()
    assert db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id).count() == before
    assert db.get(SendInstanceDB, send.id).status == "draft"


def test_a_push_send_cannot_be_tested_by_email(db, world, planned, mailed):
    _variant, send = planned("push")
    with signed_in(db) as (cookied, _token, csrf):
        response = _test(cookied, csrf, send.id)
    assert response.status_code == 409 and "push" in response.json()["detail"]
    assert mailed == []


def test_another_brands_send_is_not_found(db, world, planned, foreign_brand):
    _variant, send = planned()
    send.brand_id = foreign_brand.id
    db.commit()
    try:
        with signed_in(db) as (cookied, _token, csrf):
            response = _test(cookied, csrf, send.id)
        assert response.status_code == 404
    finally:
        send.brand_id = world["brand"].id
        db.commit()


def test_testing_needs_the_right_to_send(db, world, planned):
    _variant, send = planned()
    with machine([VIEW, SENDS_PLAN]) as headers:
        response = api.post(f"/delivery/send-instances/{send.id}/test", json={"to": "x@example.invalid"},
                            headers=headers)
    assert response.status_code == 403


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
