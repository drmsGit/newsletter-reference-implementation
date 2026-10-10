"""An approval runs only if its requester is still allowed (task-331).

ADR-142's second 2026-10-09 addendum: when a person approves a held request,
the request is re-checked against its requester's standing at that moment. A
requester that is switched off, or no longer holds the permission the action
needs, voids it — nothing runs, the request closes as `withdrawn`, audited —
and the inbox says so before anyone decides. Decided further in task-331's
final-design pass (2026-10-10): the permission is declared on the action
(`request_permission`), and people and integrations follow the same rule.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.approvals import service as approvals
from app.approvals.actions.registry import get_action
from app.approvals.db_models import PendingActionDB, WITHDRAWN
from app.audit.db_models import AuditEventDB
from app.audit.service import ACTOR_INTEGRATION, ACTOR_USER, APPROVAL_WITHDRAWN
from app.auth import integrations as ints
from app.auth import service as auth
from app.auth.db_models import IntegrationDB
from app.auth.policy import APPROVABLE_ROUTES, HELD_FOR_EVERY_INTEGRATION, required_permission
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.snapshots.service import create_snapshot_for_variant
from main import app
from tests import test_render_skip as _render_skip
from tests.test_api_guard import signed_in

db = _render_skip.db
world = _render_skip.world
SEND = "send.fire_send_instance"


@pytest.fixture
def made(db):
    """Integrations, users and requests this test creates, removed afterwards."""
    ids = {"integrations": [], "users": [], "requests": []}
    yield ids
    db.rollback()
    if ids["requests"]:
        db.query(AuditEventDB).filter(AuditEventDB.subject_type == "pending_action",
                                      AuditEventDB.subject_id.in_(ids["requests"])).delete(synchronize_session=False)
        db.query(PendingActionDB).filter(PendingActionDB.id.in_(ids["requests"])).delete(synchronize_session=False)
    for integration_id in ids["integrations"]:
        for table in ("integration_credentials", "integration_grants"):
            db.execute(text(f"DELETE FROM {table} WHERE integration_id = :i"), {"i": integration_id})
        db.execute(text("DELETE FROM integrations WHERE id = :i"), {"i": integration_id})
    for user_id in ids["users"]:
        for table in ("auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user_id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
    db.commit()


def _draft_send(db, world) -> SendInstanceDB:
    brand = world["brand"]
    snapshot = create_snapshot_for_variant(db, world["variant"](static=True, slots=0).id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-331", status="draft", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=world["person"]().id, status="created",
                               provider="mock", channel="email", purpose="marketing"))
    db.commit()
    return send


def _integration(db, world, made, permissions=("sends.execute",)) -> IntegrationDB:
    integration = ints.create_integration(db, name=f"task-331-{uuid.uuid4().hex[:6]}", description="test")
    made["integrations"].append(integration.id)
    for permission in permissions:
        assert ints.grant(db, integration.id, permission, world["brand"].id)
    return integration


def _user(db, made, role_key="admin"):
    user = auth.create_user(db, email=f"t331-{uuid.uuid4().hex[:8]}@example.invalid", role_key=role_key)
    made["users"].append(user.id)
    return user


def _held(db, world, made, send, *, by_type, by_id) -> PendingActionDB:
    row = approvals.request_approval(
        db, SEND, payload={"send_instance_id": send.id}, summary="task-331",
        requested_by_type=by_type, requested_by_id=by_id,
        brand_id=world["brand"].id, subject_id=send.id,
    )
    made["requests"].append(row.id)
    return row


def _approve(db, row, approver):
    return approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=approver.id)


def _assert_withdrawn(db, row, send, approver, world):
    db.expire_all()
    stored = db.get(PendingActionDB, row.id)
    assert stored.status == WITHDRAWN
    assert stored.decided_by_id == approver.id and "no longer allowed" in stored.decision_reason
    assert db.get(SendInstanceDB, send.id).status == "draft", "nothing ran"
    assert world["delivered"] == []
    entry = db.query(AuditEventDB).filter(AuditEventDB.action == APPROVAL_WITHDRAWN,
                                          AuditEventDB.subject_id == row.id).one()
    assert (entry.actor_type, entry.actor_id) == (ACTOR_USER, approver.id)


class TestAnIntegrationRequester:

    def test_switched_off_before_the_decision_voids_it(self, db, world, made):
        send = _draft_send(db, world)
        integration = _integration(db, world, made)
        row = _held(db, world, made, send, by_type=ACTOR_INTEGRATION, by_id=integration.id)
        ints.deactivate_integration(db, integration.id)
        approver = _user(db, made)
        world["delivered"].clear()

        result = _approve(db, row, approver)
        assert result.ok is False and "no longer allowed" in result.message
        _assert_withdrawn(db, row, send, approver, world)

    def test_losing_the_permission_voids_it(self, db, world, made):
        send = _draft_send(db, world)
        integration = _integration(db, world, made, permissions=("sends.execute", "view"))
        row = _held(db, world, made, send, by_type=ACTOR_INTEGRATION, by_id=integration.id)
        assert ints.revoke_grant(db, integration.id, "sends.execute", world["brand"].id)
        approver = _user(db, made)
        world["delivered"].clear()

        assert _approve(db, row, approver).ok is False
        _assert_withdrawn(db, row, send, approver, world)

    def test_a_still_allowed_requester_runs_as_before(self, db, world, made):
        send = _draft_send(db, world)
        integration = _integration(db, world, made)
        row = _held(db, world, made, send, by_type=ACTOR_INTEGRATION, by_id=integration.id)
        world["delivered"].clear()

        assert _approve(db, row, _user(db, made)).ok is True
        db.expire_all()
        assert db.get(PendingActionDB, row.id).status == "approved"
        assert len(world["delivered"]) == 1

    def test_a_grant_on_another_brand_does_not_count(self, db, world, foreign_brand, made):
        """The request belongs to its brand; a send right elsewhere is not standing here."""
        send = _draft_send(db, world)
        integration = _integration(db, world, made)
        row = _held(db, world, made, send, by_type=ACTOR_INTEGRATION, by_id=integration.id)
        assert ints.grant(db, integration.id, "sends.execute", foreign_brand.id)
        assert ints.revoke_grant(db, integration.id, "sends.execute", world["brand"].id)

        assert _approve(db, row, _user(db, made)).ok is False


class TestAPersonRequester:
    """One rule for everyone (decided 2026-10-10)."""

    def test_deactivated_voids_it(self, db, world, made):
        send = _draft_send(db, world)
        requester = _user(db, made)
        row = _held(db, world, made, send, by_type=ACTOR_USER, by_id=requester.id)
        requester.is_active = False
        db.commit()
        approver = _user(db, made)
        world["delivered"].clear()

        assert _approve(db, row, approver).ok is False
        _assert_withdrawn(db, row, send, approver, world)

    def test_without_the_permission_voids_it(self, db, world, made):
        send = _draft_send(db, world)
        requester = _user(db, made, role_key="viewer")
        row = _held(db, world, made, send, by_type=ACTOR_USER, by_id=requester.id)
        approver = _user(db, made)
        world["delivered"].clear()

        assert _approve(db, row, approver).ok is False
        _assert_withdrawn(db, row, send, approver, world)


def test_rejecting_is_unaffected(db, world, made):
    send = _draft_send(db, world)
    integration = _integration(db, world, made)
    row = _held(db, world, made, send, by_type=ACTOR_INTEGRATION, by_id=integration.id)
    ints.deactivate_integration(db, integration.id)

    assert approvals.reject(db, row.id, approver_type=ACTOR_USER, approver_id=_user(db, made).id, reason="no")
    db.expire_all()
    assert db.get(PendingActionDB, row.id).status == "rejected"


def test_the_inbox_says_which_requesters_are_no_longer_allowed(db, world, made):
    allowed = _integration(db, world, made)
    gone = _integration(db, world, made)
    ok_row = _held(db, world, made, _draft_send(db, world), by_type=ACTOR_INTEGRATION, by_id=allowed.id)
    void_row = _held(db, world, made, _draft_send(db, world), by_type=ACTOR_INTEGRATION, by_id=gone.id)
    ints.deactivate_integration(db, gone.id)

    with signed_in(db) as (client, _token, _csrf):
        listed = client.get("/approvals/?status=pending&limit=200").json()["items"]
        detail = client.get(f"/approvals/{void_row.id}").json()
    by_id = {item["id"]: item for item in listed}
    assert by_id[ok_row.id]["requester_allowed"] is True
    assert by_id[void_row.id]["requester_allowed"] is False
    assert detail["requester_allowed"] is False


def test_each_approvable_route_declares_what_its_requester_needed():
    """Declared, not inferred (decided 2026-10-10) — and pinned to the policy,
    so the declaration cannot drift from what the route actually checked."""
    held_methods = {template: method for method, template in HELD_FOR_EVERY_INTEGRATION}
    for template, action_key in APPROVABLE_ROUTES.items():
        method = held_methods.get(template, "POST")
        assert get_action(action_key).request_permission == required_permission(method, template), action_key
    assert get_action("ai.apply_subject_preheader").request_permission == "ai.run"


api = TestClient(app, raise_server_exceptions=False)
