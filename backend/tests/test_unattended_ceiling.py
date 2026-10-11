"""An integration's unattended sends have a recipient ceiling of their own
(task-341; ADR-166 addenda of 2026-10-09 and 2026-10-11).

The switch became a number: 0 means never (the default). A send the
integration fires is counted as of now; at or below its ceiling it goes out
unattended, above it is held for a person, with the size in the inbox. The
batch route decides send by send. Raising the ceiling is gated like switching
unattended sending on; it is never above the company cap.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.approvals.db_models import PendingActionDB
from app.auth import integrations as ints
from app.auth.db_models import IntegrationCredentialDB, IntegrationDB
from app.auth.permissions import SENDS_EXECUTE, VIEW
from app.database import SessionLocal
from app.delivery import service as delivery
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.recipients.db_models import RecipientDB
from app.settings.service import get_max_send_recipients
from app.snapshots.db_models import SnapshotDB
from main import app
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def _integration_of(db, headers) -> IntegrationDB:
    key_id = headers["Authorization"].split()[1].split(".")[0]
    return (db.query(IntegrationDB)
            .join(IntegrationCredentialDB, IntegrationCredentialDB.integration_id == IntegrationDB.id)
            .filter(IntegrationCredentialDB.key_id == key_id).one())


@pytest.fixture
def sends(db, default_brand):
    """Sends of the default brand with N planned recipients and no audience
    group, so the count as of now is the planned count."""
    snapshot = (db.query(SnapshotDB).order_by(SnapshotDB.id).first())
    if snapshot is None:
        pytest.skip("no snapshot in this database")
    recipients = [r.id for r in db.query(RecipientDB).order_by(RecipientDB.id).limit(5)]
    made: list[int] = []

    def make(planned: int, *, scheduled: bool = False) -> SendInstanceDB:
        row = SendInstanceDB(brand_id=default_brand.id, snapshot_id=snapshot.id,
                             status="scheduled" if scheduled else "draft",
                             name=f"ceiling {uuid.uuid4().hex[:6]}", provider="mock",
                             scheduled_at=(datetime.now(timezone.utc) - timedelta(minutes=5)) if scheduled else None)
        db.add(row)
        db.flush()
        for recipient_id in recipients[:planned]:
            db.add(DeliveryExecutionDB(send_instance_id=row.id, recipient_id=recipient_id, status="created",
                                       provider="mock", channel="email", purpose="marketing"))
        db.commit()
        made.append(row.id)
        return row

    yield make
    db.rollback()
    db.query(PendingActionDB).filter(PendingActionDB.subject_type == "send_instance",
                                     PendingActionDB.subject_id.in_(made)).delete(synchronize_session=False)
    db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id.in_(made)).delete(
        synchronize_session=False)
    db.query(SendInstanceDB).filter(SendInstanceDB.id.in_(made)).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def fired(monkeypatch):
    """What the fire route and the sweep fire, instead of sending."""
    calls: list[int] = []

    def fake(db, *args, send_instance_id=None, brand_id=None, **kwargs):
        calls.append(send_instance_id if send_instance_id is not None else args[0])
        return None

    import app.delivery.router as router

    monkeypatch.setattr(router, "send_send_instance", fake)
    monkeypatch.setattr(delivery, "send_send_instance", fake)
    return calls


def _pending(db, send_id):
    db.expire_all()
    return db.query(PendingActionDB).filter(PendingActionDB.subject_type == "send_instance",
                                            PendingActionDB.subject_id == send_id).all()


# --- the fire route ------------------------------------------------------------------

def test_at_the_ceiling_the_send_fires_unattended(db, sends, fired):
    send = sends(3)
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        ints.set_unattended_ceiling(db, _integration_of(db, headers).id, 3)
        response = api.post(f"/delivery/send-instances/{send.id}/send", headers=headers)
    assert response.status_code != 202, response.text
    assert send.id in fired and _pending(db, send.id) == []


def test_above_the_ceiling_it_is_held_for_its_size(db, sends, fired):
    send = sends(3)
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        ints.set_unattended_ceiling(db, _integration_of(db, headers).id, 2)
        response = api.post(f"/delivery/send-instances/{send.id}/send", headers=headers)
    assert response.status_code == 202, response.text
    assert fired == []
    [held] = _pending(db, send.id)
    assert held.payload["held_for_size"] == {"recipients": 3, "ceiling": 2}
    assert "3 recipients" in held.summary and "limit of 2" in held.summary


def test_the_inbox_says_it_was_held_for_its_size(db, sends, fired):
    from app.approvals.actions.send_fire import describe

    send = sends(3)
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        ints.set_unattended_ceiling(db, _integration_of(db, headers).id, 2)
        api.post(f"/delivery/send-instances/{send.id}/send", headers=headers)
    [held] = _pending(db, send.id)
    described = describe(db, held.payload, brand_id=send.brand_id)
    assert any("limit of 2" in w and "3 recipients" in w for w in described.warnings), described.warnings


def test_a_ceiling_of_zero_holds_every_send(db, sends, fired):
    send = sends(1)
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        response = api.post(f"/delivery/send-instances/{send.id}/send", headers=headers)
    assert response.status_code == 202 and fired == []


def test_zero_means_never_even_for_a_send_with_nobody_planned(db, sends, fired):
    send = sends(0)
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        response = api.post(f"/delivery/send-instances/{send.id}/send", headers=headers)
    assert response.status_code == 202 and fired == []


def test_recipients_already_sent_do_not_count(db, sends, fired):
    """A retried send counts who is still to be mailed, not who already was."""
    send = sends(4)
    rows = (db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id)
            .order_by(DeliveryExecutionDB.id).all())
    for row in rows[:2]:
        row.status = "sent"
    db.commit()
    assert delivery.recipients_now(db, send) == 2
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        ints.set_unattended_ceiling(db, _integration_of(db, headers).id, 2)
        response = api.post(f"/delivery/send-instances/{send.id}/send", headers=headers)
    assert response.status_code != 202 and send.id in fired


def test_the_count_is_the_audience_as_of_now(db, sends, default_brand):
    """A send planned small whose audience has grown counts as it is now."""
    from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
    from app.audience.service import add_member, create_group, resolve_audience

    group = create_group(db, f"Ceiling {uuid.uuid4().hex[:6]}", brand_id=default_brand.id)
    consenting = [r.id for r in resolve_audience(db, group.id, channel="email")]  # empty group
    assert consenting == []
    seeded = db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == default_brand.id,
                                             AudienceGroupDB.id != group.id).first()
    members = [r.id for r in resolve_audience(db, seeded.id, channel="email")][:3] if seeded else []
    if len(members) < 3:
        pytest.skip("the seed has no audience of three")
    send = sends(1)
    send.audience_group_id = group.id
    db.commit()
    try:
        for recipient_id in members:
            add_member(db, group.id, recipient_id, brand_id=default_brand.id)
        assert delivery.recipients_now(db, send) == 3
    finally:
        send.audience_group_id = None
        db.commit()
        db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group.id).delete()
        db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
        db.commit()


# --- the batch -----------------------------------------------------------------------

def test_the_batch_holds_the_large_send_and_fires_the_small_one(db, sends, fired):
    small, large = sends(1, scheduled=True), sends(3, scheduled=True)
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        ints.set_unattended_ceiling(db, _integration_of(db, headers).id, 2)
        response = api.post("/delivery/process-due", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert small.id in body["send_instance_ids"] and large.id not in body["send_instance_ids"]
    assert large.id in body["held_send_instance_ids"]
    assert small.id in fired and large.id not in fired
    [held] = _pending(db, large.id)
    assert held.payload["held_for_size"] == {"recipients": 3, "ceiling": 2}
    db.expire_all()
    assert db.get(SendInstanceDB, large.id).status == "scheduled", "a held send stays scheduled"


def test_a_person_running_the_batch_has_no_ceiling(db, sends, fired):
    from tests.test_api_guard import signed_in

    large = sends(3, scheduled=True)
    with signed_in(db) as (client, _token, csrf):
        response = client.post("/delivery/process-due", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200, response.text
    assert large.id in response.json()["send_instance_ids"]


# --- setting it ------------------------------------------------------------------------

def test_the_ceiling_is_never_above_the_company_cap(db):
    with machine([VIEW]) as headers:
        integration = _integration_of(db, headers)
        with pytest.raises(ValueError, match="cap"):
            ints.set_unattended_ceiling(db, integration.id, get_max_send_recipients(db) + 1)
        with pytest.raises(ValueError):
            ints.set_unattended_ceiling(db, integration.id, -1)


def test_raising_is_gated_like_switching_on_and_lowering_is_not(db, foreign_brand):
    """A person who does not hold the integration's grants may not raise its
    ceiling (no escalation), but may always lower it."""
    from app.auth import service as auth

    user = auth.create_user(db, email=f"ceil-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin")
    with machine([VIEW, SENDS_EXECUTE], brand_id=foreign_brand.id) as headers:
        integration = _integration_of(db, headers)
        try:
            with pytest.raises(ints.GrantForbidden):
                ints.set_unattended_by_person(db, user, integration.id, 50)
            ints.set_unattended_ceiling(db, integration.id, 50)
            assert ints.set_unattended_by_person(db, user, integration.id, 10)
            db.refresh(integration)
            assert integration.unattended_ceiling == 10
        finally:
            from sqlalchemy import text

            db.rollback()
            for table in ("login_codes", "auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()


def test_the_json_route_sets_a_number_and_audits_the_change(db):
    from app.audit.db_models import AuditEventDB
    from tests.test_api_guard import signed_in

    with machine([VIEW]) as headers:
        integration = _integration_of(db, headers)
        with signed_in(db) as (client, _token, csrf):
            response = client.put(f"/integrations/{integration.id}/unattended", json={"ceiling": 25},
                                  headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json()["unattended_ceiling"] == 25
        entry = (db.query(AuditEventDB).filter(AuditEventDB.action == "integration.unattended_set",
                                               AuditEventDB.subject_id == integration.id)
                 .order_by(AuditEventDB.id.desc()).first())
        assert entry.detail == {"from": 0, "to": 25}


def test_a_test_send_needs_a_ceiling_of_at_least_one(db):
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        response = api.post("/delivery/send-test", json={"to": "x@example.invalid", "subject": "t",
                                                          "provider": "mock"}, headers=headers)
    assert response.status_code == 403, response.text
