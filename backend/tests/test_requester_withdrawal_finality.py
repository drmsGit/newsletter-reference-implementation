"""Restored access cannot revive a withdrawn approval (task-331, ADR-142)."""
import pytest

from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


@pytest.fixture
def made(db):
    from tests.test_requester_standing import made as standing_made

    yield from standing_made.__wrapped__(db)


@pytest.mark.parametrize("lost_access", ["inactive", "revoked"])
def test_restoring_access_does_not_revive_a_withdrawn_send(db, world, made, lost_access):
    from app.audit.service import ACTOR_INTEGRATION
    from app.auth import integrations as ints
    from tests.test_requester_standing import (
        _approve, _assert_withdrawn, _draft_send, _held, _integration, _user,
    )

    send = _draft_send(db, world)
    requester = _integration(db, world, made)
    row = _held(db, world, made, send, by_type=ACTOR_INTEGRATION, by_id=requester.id)
    approver = _user(db, made)
    world["delivered"].clear()

    if lost_access == "inactive":
        ints.deactivate_integration(db, requester.id)
    else:
        assert ints.revoke_grant(db, requester.id, "sends.execute", world["brand"].id)
    assert _approve(db, row, approver).ok is False
    _assert_withdrawn(db, row, send, approver, world)

    if lost_access == "inactive":
        requester.is_active = True
        db.commit()
    else:
        assert ints.grant(db, requester.id, "sends.execute", world["brand"].id)

    assert _approve(db, row, approver).ok is False
    _assert_withdrawn(db, row, send, approver, world)
