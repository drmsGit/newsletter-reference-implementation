"""Concurrent administration must leave an active manager (task-358; ADR-150)."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
import uuid

import pytest

from app.auth import service
from app.auth.db_models import RoleAssignmentDB, UserDB
from app.auth.permissions import USERS_MANAGE, VIEW
from app.database import SessionLocal
from tests.test_admin_routes import db  # noqa: F401


@pytest.fixture
def two_managers(db):  # noqa: F811
    previous = dict(db.query(UserDB.id, UserDB.is_active))
    suffix = uuid.uuid4().hex[:8]
    people, roles, grants = [], [], []
    try:
        for index in range(2):
            role = service.create_role(db, key=f"t358-race-{suffix}-{index}", name="Race manager")
            service.set_role_permissions(db, role.id, [VIEW, USERS_MANAGE])
            user = service.create_user(db, email=f"t358-race-{suffix}-{index}@example.invalid", role_key=role.key)
            people.append(user.id)
            roles.append(role.id)
            grants.append(db.query(RoleAssignmentDB.id).filter_by(user_id=user.id, role_id=role.id).scalar())
        # Only the isolated checkout's test database is touched. Existing people
        # are restored before the imported fixture removes our test accounts.
        db.query(UserDB).filter(UserDB.id.notin_(people)).update({"is_active": False}, synchronize_session=False)
        db.commit()
        assert service.user_managers(db) == set(people)
        yield people, roles, grants
    finally:
        db.rollback()
        for user_id, active in previous.items():
            db.query(UserDB).filter_by(id=user_id).update({"is_active": active}, synchronize_session=False)
        db.commit()


@pytest.mark.parametrize("change", ["deactivate", "revoke", "permissions"])
def test_overlapping_changes_cannot_remove_both_remaining_managers(db, two_managers, monkeypatch, change):  # noqa: F811
    people, roles, grants = two_managers
    first_ready, second_ready = Event(), Event()
    lock = Lock()
    calls = 0
    original = service._refuse_lockout

    def overlapping_guard(session, before, after):
        nonlocal calls
        with lock:
            position = calls
            calls += 1
        if position == 0:
            first_ready.set()
            # If the implementation serializes first, the second check waits
            # for this one to commit and then must refuse the last removal.
            second_ready.wait(2)
        else:
            second_ready.set()
        return original(session, before, after)

    monkeypatch.setattr(service, "_refuse_lockout", overlapping_guard)

    def act(index):
        with SessionLocal() as session:
            try:
                if change == "deactivate":
                    service.set_active(session, people[index], False, actor_user_id=people[1 - index])
                elif change == "revoke":
                    service.revoke_assignment(session, grants[index])
                else:
                    service.set_role_permissions(session, roles[index], [VIEW])
            except service.AccessLockout:
                session.rollback()
                return "refused"
            return "changed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(act, 0)
        assert first_ready.wait(5), "first removal did not reach its guard"
        second = pool.submit(act, 1)
        outcomes = [first.result(timeout=10), second.result(timeout=10)]
    with SessionLocal() as observer:
        remaining = service.user_managers(observer)
    assert sorted(outcomes) == ["changed", "refused"], f"one removal must be refused; remaining managers: {remaining}"
    assert len(remaining) == 1 and remaining <= set(people), "the installation must retain an active manager"


def test_integration_management_does_not_grant_user_administration(db):  # noqa: F811
    from app.auth.permissions import INTEGRATIONS_MANAGE
    from tests.test_brand_profile_api import person_with

    with person_with(db, [VIEW, INTEGRATIONS_MANAGE]) as (client, _headers):
        assert client.get("/integrations").status_code == 200
        assert client.get("/auth/permissions").status_code == 403
        assert client.get("/auth/brands").status_code == 403
