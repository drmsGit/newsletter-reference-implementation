"""Response models carry what their source holds and a screen needs (task-208).

Three times a screen found its response model dropping fields the table or
manifest stores. SendInstance was fixed with task-28; these pin the other two
named instances: a module's field metadata (an authoring form needs the label,
whether the field is envelope, its type and size) and a held action's subject
and decision (the inbox needs to link to what is being decided, and decision
history needs who decided and why).

**`payload` stays out on purpose.** It is the action's internal arguments; the
detail's `rows` are the readable version, produced by the action itself.
"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.approvals.db_models import PendingActionDB
from app.auth import service as auth
from app.auth.permissions import VIEW
from app.database import SessionLocal
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


def test_a_module_field_says_what_an_authoring_form_needs():
    with machine([VIEW]) as headers:
        response = client.get("/modules", params={"channel": "email"}, headers=headers)
    assert response.status_code == 200, response.text
    fields = {v["name"]: v for m in response.json() for v in m["variables"]}
    assert fields, "no email module declares a field"
    some = next(iter(fields.values()))
    assert {"label", "envelope", "type", "size", "note", "concept"} <= set(some)
    # The envelope flag is declared per field (ADR-162 point 1): subject is one.
    assert fields["subject"]["envelope"] is True
    assert any(not v["envelope"] for v in fields.values())


def test_a_held_action_names_its_subject_and_its_decision():
    db = SessionLocal()
    brand = auth.ensure_default_brand(db)
    now = datetime.now(timezone.utc)
    row = PendingActionDB(
        action_key="no-such-action", payload={"internal": "argument"}, summary="a test row",
        requested_by_type="user", requested_by_id=1, subject_type="send_instance", subject_id=42,
        brand_id=brand.id, status="failed", expires_at=now + timedelta(hours=1),
        decided_at=now, decided_by_type="user", decided_by_id=7,
        decision_reason="looked fine", execution_error="the action declined to run",
    )
    db.add(row)
    db.commit()
    try:
        with machine([VIEW]) as headers:
            listed = client.get("/approvals/", params={"status": "all"}, headers=headers)
            detail = client.get(f"/approvals/{row.id}", headers=headers)
        assert listed.status_code == 200 and detail.status_code == 200, detail.text
        mine = next(r for r in listed.json() if r["id"] == row.id)
        for body in (mine, detail.json()):
            assert (body["subject_type"], body["subject_id"]) == ("send_instance", 42)
            assert (body["decided_by_type"], body["decided_by_id"]) == ("user", 7)
            assert body["decision_reason"] == "looked fine"
            assert "payload" not in body, "the action's internal arguments leaked"
        # Why it failed: on the detail, not on every inbox row.
        assert detail.json()["execution_error"] == "the action declined to run"
        assert "execution_error" not in mine
    finally:
        db.query(PendingActionDB).filter(PendingActionDB.id == row.id).delete()
        db.commit()
        db.close()


# --- found by the sweep across every response model (2026-10-03) -----------

def _admin(db):
    from tests.test_api_guard import signed_in
    return signed_in(db)


def _demo_send(db):
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB

    send = db.query(SendInstanceDB).filter(SendInstanceDB.name == "Demo send").one()
    execution = db.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.send_instance_id == send.id).first()
    return send, execution


def test_an_execution_says_its_channel_and_purpose():
    """Without them a client cannot tell an email delivery from a push one."""
    db = SessionLocal()
    try:
        send, _ = _demo_send(db)
        with _admin(db) as (c, _token, _csrf):
            rows = c.get(f"/delivery/send-instances/{send.id}/executions").json()
        assert rows and {"channel", "purpose"} <= set(rows[0])
        assert (rows[0]["channel"], rows[0]["purpose"]) == ("email", "marketing")
    finally:
        db.close()


def test_a_recipients_activity_says_why_a_delivery_was_not_sent():
    """ADR-163 point 8: 'why didn't this person get it' is the question the
    exclusion reason exists to answer, and the activity page could not."""
    db = SessionLocal()
    try:
        _, execution = _demo_send(db)
        # A value the model's default (None) cannot fake, restored afterwards.
        execution.exclusion_reason = "consent: withdrawn"
        db.commit()
        with _admin(db) as (c, _token, _csrf):
            body = c.get(f"/recipients/{execution.recipient_id}/activity").json()
        delivery = next(d for d in body["deliveries"] if d["id"] == execution.id)
        assert delivery["exclusion_reason"] == "consent: withdrawn"
        assert delivery["purpose"] == "marketing"
    finally:
        db.rollback()
        execution.exclusion_reason = None
        db.commit()
        db.close()


def test_a_suggested_group_names_the_campaign_it_came_from():
    """It is what makes Recalculate meaningful, and null for a hand-made group."""
    from app.audience.db_models import AudienceGroupDB

    db = SessionLocal()
    try:
        _, execution = _demo_send(db)
        from app.campaigns.db_models import CampaignDB
        campaign = db.query(CampaignDB).filter(CampaignDB.name == "Demo Campaign 1").one()
        with _admin(db) as (c, _token, csrf):
            made = c.post("/api/audience-groups/suggested", json={"campaign_id": campaign.id},
                          headers={"X-CSRF-Token": csrf})
            assert made.status_code == 201, made.text
            assert made.json()["source_campaign_id"] == campaign.id
            listed = c.get("/api/audience-groups/").json()
            # Through the API's own delete, which removes the group's blocks too.
            assert c.delete(f"/api/audience-groups/{made.json()['id']}",
                            headers={"X-CSRF-Token": csrf}).status_code == 204
        assert all("source_campaign_id" in g for g in listed)
        assert db.query(AudienceGroupDB).filter(AudienceGroupDB.id == made.json()["id"]).count() == 0
    finally:
        db.close()


def test_an_address_says_whether_it_is_primary_and_verified():
    from app.recipients.db_models import RecipientDB

    from datetime import datetime, timezone

    from app.recipients.db_models import AddressabilityDB

    db = SessionLocal()
    try:
        recipient = db.query(RecipientDB).filter(RecipientDB.external_id.isnot(None)).first()
        address = db.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == recipient.id).first()
        assert address is not None, "the seeded recipient has no address"
        before = (address.is_primary, address.verified_at)
        # Values the model's defaults (False, None) cannot fake.
        address.is_primary = True
        address.verified_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        db.commit()
        with _admin(db) as (c, _token, _csrf):
            body = c.get(f"/recipients/{recipient.external_id}").json()
        shown = next(a for a in body["addresses"] if a["channel"] == address.channel)
        assert shown["is_primary"] is True
        assert shown["verified_at"].startswith("2026-09-01")
    finally:
        db.rollback()
        address.is_primary, address.verified_at = before
        db.commit()
        db.close()


def test_one_recipient_can_be_read_at_all():
    """Regression: from 2026-09-16 to 2026-10-03 this raised TypeError — the
    service dropped the brand that consent is projected for — and returned 500
    for every recipient. Found by the sweep's own test above."""
    from app.recipients.db_models import RecipientDB

    db = SessionLocal()
    try:
        recipient = db.query(RecipientDB).filter(RecipientDB.external_id.isnot(None)).first()
        with _admin(db) as (c, _token, _csrf):
            response = c.get(f"/recipients/{recipient.external_id}")
        assert response.status_code == 200, response.text[:200]
        assert response.json()["external_id"] == recipient.external_id
    finally:
        db.close()
