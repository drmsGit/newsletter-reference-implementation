"""Release boundaries for task-325/326 (ADR-192 and ADR-142)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.audit.db_models import AuditEventDB
from app.delivery import service as delivery
from app.delivery.db_models import SendInstanceDB
from tests import test_render_skip as _fixtures
from tests.test_api_guard import signed_in

db = _fixtures.db
world = _fixtures.world


def _release(db, send_id):
    with signed_in(db) as (client, _token, csrf):
        return client.post(f"/delivery/send-instances/{send_id}/release",
                           headers={"X-CSRF-Token": csrf})


def test_release_rechecks_activity_after_the_screen_flag(db, world):
    from tests.test_stranded_send import _stranded

    send, states = _stranded(db, world, idle=timedelta(hours=2))
    send_id = send.id
    assert delivery.send_instance_detail(db, send_id, brand_id=world["brand"].id).stranded
    db.execute(text("UPDATE delivery_executions SET updated_at = now() "
                    "WHERE send_instance_id = :s AND recipient_id = :r"),
               {"s": send_id, "r": states["sending"].id})
    db.commit()
    assert _release(db, send_id).status_code == 409
    db.expire_all()
    assert db.get(SendInstanceDB, send_id).status == "sending"
    assert db.query(AuditEventDB).filter_by(action="send.released", subject_id=send_id).count() == 0
    assert world["delivered"] == []


def test_release_cannot_change_a_send_in_another_brand(db, world):
    from tests.test_stranded_send import _stranded

    send, _ = _stranded(db, world, idle=timedelta(hours=2))
    send_id = send.id
    with pytest.raises(LookupError):
        delivery.release_send_instance(db, send_id, brand_id=world["brand"].id + 1000000)
    db.rollback()
    assert db.get(SendInstanceDB, send_id).status == "sending"
    assert world["delivered"] == []


def test_held_request_failure_rolls_back_release_and_allows_a_clean_retry(db, world, monkeypatch):
    from app.approvals import service as approvals
    from app.approvals.db_models import PendingActionDB
    from tests.test_stranded_send import _stranded

    send, _ = _stranded(db, world, idle=timedelta(hours=2))
    send_id = send.id
    request = PendingActionDB(
        action_key="send.fire_send_instance", payload={"send_instance_id": send_id},
        summary="release rollback regression", requested_by_type="integration",
        subject_type="send_instance", subject_id=send_id, brand_id=world["brand"].id,
        status="executing", expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        decided_at=datetime.now(timezone.utc), decided_by_type="user",
    )
    db.add(request)
    db.commit()
    request_id = request.id
    real_fail = approvals.fail_stuck_requests

    def fail_after_flush(*args, **kwargs):
        assert real_fail(*args, **kwargs) == [request_id]
        raise RuntimeError("injected failure after held-request flush")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(approvals, "fail_stuck_requests", fail_after_flush)
            assert _release(db, send_id).status_code == 500
        db.rollback()
        db.expire_all()
        assert db.get(SendInstanceDB, send_id).status == "sending"
        assert db.get(PendingActionDB, request_id).status == "executing"
        assert db.query(AuditEventDB).filter_by(action="send.released", subject_id=send_id).count() == 0
        assert db.query(AuditEventDB).filter_by(action="approval.failed", subject_id=request_id).count() == 0
        assert _release(db, send_id).status_code == 200
        db.expire_all()
        assert db.get(SendInstanceDB, send_id).status == "failed"
        assert db.get(PendingActionDB, request_id).status == "failed"
        assert db.query(AuditEventDB).filter_by(action="send.released", subject_id=send_id).count() == 1
        assert db.query(AuditEventDB).filter_by(action="approval.failed", subject_id=request_id).count() == 1
        assert world["delivered"] == []
    finally:
        db.rollback()
        db.query(AuditEventDB).filter_by(subject_type="pending_action", subject_id=request_id).delete()
        db.query(PendingActionDB).filter_by(id=request_id).delete()
        db.commit()
