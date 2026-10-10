"""The approvals history says what an approved send ended in (task-338).

The history's Outcome showed only the request's own status, so a send in which
every delivery failed read "approved". Decided 2026-10-09 (Manager Workflow
interview, Cluster 1 Q6): the history shows the result as a plain fact, linked
to the send, and nobody is notified. Decided 2026-10-10: the send as it is now,
read live — a retry or a release changes what it says.
"""
import uuid

from sqlalchemy import text

from app.approvals import service as approvals
from app.approvals.db_models import PendingActionDB
from app.audit.db_models import AuditEventDB
from app.audit.service import ACTOR_INTEGRATION, ACTOR_USER
from app.auth import integrations as ints
from app.auth import service as auth
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.delivery.providers.base import SendResult
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip
from tests.test_api_guard import signed_in

db = _render_skip.db
world = _render_skip.world


def _approved_send(db, world, monkeypatch, *, fail=False):
    brand = world["brand"]
    snapshot = create_snapshot_for_variant(db, world["variant"](static=True, slots=0).id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-338", status="draft", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    for _ in range(2):
        db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=world["person"]().id, status="created",
                                   provider="mock", channel="email", purpose="marketing"))
    db.commit()
    integration = ints.create_integration(db, name=f"t338-{uuid.uuid4().hex[:6]}", description="test")
    assert ints.grant(db, integration.id, "sends.execute", brand.id)
    approver = auth.create_user(db, email=f"t338-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin")
    row = approvals.request_approval(
        db, "send.fire_send_instance", payload={"send_instance_id": send.id}, summary="task-338",
        requested_by_type=ACTOR_INTEGRATION, requested_by_id=integration.id, brand_id=brand.id, subject_id=send.id)
    if fail:
        monkeypatch.setattr(mock_module.MockProvider, "send",
                            lambda self, address, artifact: SendResult(success=False, message="mailbox full"))
    assert approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=approver.id).ok
    return send, row, integration, approver


def _cleanup(db, row, integration, approver):
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "pending_action",
                                  AuditEventDB.subject_id == row.id).delete(synchronize_session=False)
    db.query(PendingActionDB).filter(PendingActionDB.id == row.id).delete(synchronize_session=False)
    for table in ("integration_credentials", "integration_grants"):
        db.execute(text(f"DELETE FROM {table} WHERE integration_id = :i"), {"i": integration.id})
    db.execute(text("DELETE FROM integrations WHERE id = :i"), {"i": integration.id})
    for table in ("auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": approver.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": approver.id})
    db.commit()


def _history_row(db, row_id):
    with signed_in(db) as (client, _token, _csrf):
        items = client.get("/approvals/?status=decided&limit=200").json()["items"]
    return next(item for item in items if item["id"] == row_id)


def test_an_approved_send_that_failed_says_so(db, world, monkeypatch):
    send, row, integration, approver = _approved_send(db, world, monkeypatch, fail=True)
    try:
        item = _history_row(db, row.id)
        assert item["status"] == "approved"
        assert item["outcome"] == "Failed: 0 delivered, 2 failed, 0 excluded."
        assert (item["subject_type"], item["subject_id"]) == ("send_instance", send.id)
    finally:
        _cleanup(db, row, integration, approver)


def test_it_reads_the_send_as_it_is_now(db, world, monkeypatch):
    """A retry after the approval changes what the history says."""
    send, row, integration, approver = _approved_send(db, world, monkeypatch, fail=True)
    try:
        db.execute(text("UPDATE send_instances SET status = 'partial_failed', sent_count = 1, failed_count = 1 "
                        "WHERE id = :s"), {"s": send.id})
        db.commit()
        assert _history_row(db, row.id)["outcome"] == "Partial failed: 1 delivered, 1 failed, 0 excluded."
    finally:
        _cleanup(db, row, integration, approver)


def test_a_request_that_is_not_approved_has_no_outcome(db, world):
    """Only an approved request ran; a rejected one has nothing to report."""
    send_row = SendInstanceDB(brand_id=world["brand"].id, name="task-338 rejected", status="draft", provider="mock",
                              snapshot_id=create_snapshot_for_variant(
                                  db, world["variant"](static=True, slots=0).id, brand_id=world["brand"].id).id)
    db.add(send_row)
    db.commit()
    world["made"]["snapshots"].append(send_row.snapshot_id)
    world["made"]["sends"].append(send_row.id)
    integration = ints.create_integration(db, name=f"t338-{uuid.uuid4().hex[:6]}", description="test")
    approver = auth.create_user(db, email=f"t338-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin")
    row = approvals.request_approval(
        db, "send.fire_send_instance", payload={"send_instance_id": send_row.id}, summary="task-338",
        requested_by_type=ACTOR_INTEGRATION, requested_by_id=integration.id, brand_id=world["brand"].id,
        subject_id=send_row.id)
    try:
        assert approvals.reject(db, row.id, approver_type=ACTOR_USER, approver_id=approver.id, reason="no")
        assert _history_row(db, row.id)["outcome"] is None
    finally:
        _cleanup(db, row, integration, approver)
