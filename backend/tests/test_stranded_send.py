"""A send stranded in "sending" is flagged, and a person releases it (task-325, ADR-192).

A process that dies mid-send leaves the send `sending` for good, and the
double-send guard then refuses every retry. Decided with the user 2026-10-09
(option 3): the platform flags a send with no activity for 30 minutes; it
never releases one by itself, because no timeout can tell a slow live send
from a dead one with certainty. A person releases it, which makes it `failed`
— and the retry then follows task-318: sent stays sent, the in-flight
recipient becomes uncertain, the never-attempted one is sent.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit.db_models import AuditEventDB
from app.auth.permissions import SENDS_PLAN
from app.delivery import service as delivery
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.snapshots.service import create_snapshot_for_variant
from main import app
from tests import test_render_skip as _render_skip
from tests.machine import machine
from tests.test_api_guard import signed_in

api = TestClient(app, raise_server_exceptions=False)
db = _render_skip.db
world = _render_skip.world


def _stranded(db, world, *, idle: timedelta) -> tuple[SendInstanceDB, dict]:
    """What a process dying mid-send leaves behind: the send `sending`, one
    recipient sent, one in flight (`sending`), one never attempted."""
    brand = world["brand"]
    people = [world["person"]() for _ in range(3)]
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-325", status="sending", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    states = dict(zip(("sent", "sending", "created"), people))
    for status, person in states.items():
        db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status=status,
                                   provider="mock", channel="email", purpose="marketing",
                                   provider_message_id=f"mock-old-{send.id}-{person.id}" if status == "sent" else None))
    db.commit()
    then = datetime.now(timezone.utc) - idle
    db.execute(text("UPDATE send_instances SET updated_at = :t WHERE id = :s"), {"t": then, "s": send.id})
    db.execute(text("UPDATE delivery_executions SET updated_at = :t WHERE send_instance_id = :s"),
               {"t": then, "s": send.id})
    db.commit()
    db.expire_all()
    return send, states


class TestTheFlag:

    def test_a_quiet_sending_send_is_flagged(self, db, world):
        send, _ = _stranded(db, world, idle=timedelta(hours=2))
        detail = delivery.send_instance_detail(db, send.id, brand_id=world["brand"].id)
        assert detail.stranded is True and detail.last_activity_at is not None
        listed = delivery.list_send_instances(db, brand_id=world["brand"].id, status="sending")
        assert any(s.id == send.id and s.stranded for s in listed.items)

    def test_a_send_with_recent_activity_is_not(self, db, world):
        send, _ = _stranded(db, world, idle=timedelta(minutes=5))
        assert delivery.send_instance_detail(db, send.id, brand_id=world["brand"].id).stranded is False

    def test_a_living_send_whose_recipients_keep_moving_is_not(self, db, world):
        """The send row itself is written once, at the start; what shows a
        living send is its recipients being written one by one (task-318)."""
        send, states = _stranded(db, world, idle=timedelta(hours=2))
        db.execute(text("UPDATE delivery_executions SET updated_at = now() WHERE send_instance_id = :s "
                        "AND recipient_id = :r"), {"s": send.id, "r": states["sending"].id})
        db.commit()
        assert delivery.send_instance_detail(db, send.id, brand_id=world["brand"].id).stranded is False

    def test_a_finished_send_is_never_stranded(self, db, world):
        send, _ = _stranded(db, world, idle=timedelta(hours=2))
        # Keep the old timestamp: a status change would otherwise bump it and
        # make the send look recent, which is not what this asserts.
        db.execute(text("UPDATE send_instances SET status = 'failed', updated_at = updated_at WHERE id = :s"),
                   {"s": send.id})
        db.commit()
        assert delivery.send_instance_detail(db, send.id, brand_id=world["brand"].id).stranded is False


class TestRelease:

    def test_a_person_releases_a_stranded_send_and_the_retry_follows_task_318(self, db, world):
        send, states = _stranded(db, world, idle=timedelta(hours=2))
        with signed_in(db) as (client, _token, csrf):
            response = client.post(f"/delivery/send-instances/{send.id}/release", headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "failed"
        db.expire_all()
        entry = (db.query(AuditEventDB).filter(AuditEventDB.action == "send.released",
                                               AuditEventDB.subject_id == send.id).one())
        assert entry.detail["executions"] == {"sent": 1, "sending": 1, "created": 1}

        world["delivered"].clear()
        assert delivery.send_send_instance(db, send.id, brand_id=world["brand"].id) == "partial_failed"
        db.expire_all()
        rows = {e.recipient_id: e.status for e in db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id)}
        assert rows[states["sent"].id] == "sent"
        assert rows[states["sending"].id] == "uncertain"
        assert rows[states["created"].id] == "sent"
        assert len(world["delivered"]) == 1, "only the never-attempted recipient is mailed"

    def test_a_live_send_cannot_be_released(self, db, world):
        send, _ = _stranded(db, world, idle=timedelta(minutes=5))
        with signed_in(db) as (client, _token, csrf):
            response = client.post(f"/delivery/send-instances/{send.id}/release", headers={"X-CSRF-Token": csrf})
        assert response.status_code == 409
        db.expire_all()
        assert db.get(SendInstanceDB, send.id).status == "sending"

    def test_a_machine_cannot_release(self, db, world):
        send, _ = _stranded(db, world, idle=timedelta(hours=2))
        with machine([SENDS_PLAN], brand_id=world["brand"].id) as headers:
            response = api.post(f"/delivery/send-instances/{send.id}/release", headers=headers)
        assert response.status_code == 403
        db.expire_all()
        assert db.get(SendInstanceDB, send.id).status == "sending"


def test_the_service_refuses_what_is_not_stranded(db, world):
    send, _ = _stranded(db, world, idle=timedelta(minutes=5))
    with pytest.raises(ValueError, match="not stranded"):
        delivery.release_send_instance(db, send.id, brand_id=world["brand"].id)


class TestTheHeldRequest:
    """task-326, option 3 (ADR-142 addendum 2026-10-09): releasing a stranded
    send also fails the held request whose approval was running it, so a new
    request can be raised. The send's release already establishes the run died.
    """

    @pytest.fixture
    def held(self, db):
        from app.approvals.db_models import PendingActionDB

        made: list[int] = []

        def make(send_id: int, *, status: str = "executing", action_key: str = "send.fire_send_instance") -> int:
            decided = status != "pending"
            row = PendingActionDB(
                action_key=action_key, payload={"send_instance_id": send_id}, summary="task-326",
                requested_by_type="integration", subject_type="send_instance", subject_id=send_id,
                brand_id=1, status=status,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                decided_at=datetime.now(timezone.utc) if decided else None,
                decided_by_type="user" if decided else None,
            )
            db.add(row)
            db.commit()
            made.append(row.id)
            return row.id

        yield make
        db.rollback()
        db.query(PendingActionDB).filter(PendingActionDB.id.in_(made)).delete(synchronize_session=False)
        db.query(AuditEventDB).filter(AuditEventDB.subject_type == "pending_action",
                                      AuditEventDB.subject_id.in_(made)).delete(synchronize_session=False)
        db.commit()

    def _release(self, db, send_id):
        with signed_in(db) as (client, _token, csrf):
            return client.post(f"/delivery/send-instances/{send_id}/release", headers={"X-CSRF-Token": csrf})

    def test_releasing_the_send_fails_its_stuck_request_and_frees_the_subject(self, db, world, held):
        from app.approvals.db_models import PendingActionDB

        send, _ = _stranded(db, world, idle=timedelta(hours=2))
        stuck = held(send.id)
        assert self._release(db, send.id).status_code == 200
        db.expire_all()
        row = db.get(PendingActionDB, stuck)
        assert row.status == "failed" and "released" in row.execution_error
        entry = db.query(AuditEventDB).filter(AuditEventDB.action == "approval.failed",
                                              AuditEventDB.subject_id == stuck).one()
        assert entry.actor_type == "user" and entry.actor_id is not None
        held(send.id, status="pending")      # a new request for the same send is allowed again

    def test_other_requests_are_untouched(self, db, world, held):
        from app.approvals.db_models import PendingActionDB

        send, _ = _stranded(db, world, idle=timedelta(hours=2))
        other_send, _ = _stranded(db, world, idle=timedelta(hours=2))
        elsewhere = held(other_send.id)
        other_action = held(send.id, action_key="content.mark_ready")
        assert self._release(db, send.id).status_code == 200
        db.expire_all()
        assert db.get(PendingActionDB, elsewhere).status == "executing"
        assert db.get(PendingActionDB, other_action).status == "executing"

    def test_a_refused_release_leaves_the_request_alone(self, db, world, held):
        from app.approvals.db_models import PendingActionDB

        send, _ = _stranded(db, world, idle=timedelta(minutes=5))
        stuck = held(send.id)
        assert self._release(db, send.id).status_code == 409
        db.expire_all()
        assert db.get(PendingActionDB, stuck).status == "executing"
