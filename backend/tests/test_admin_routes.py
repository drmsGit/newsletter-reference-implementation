"""People, roles and brands over JSON, and the lock-out guards (task-358;
ADR-150 addendum 2026-10-16).

People only, users.manage for reads too. Every write goes through
app/auth/admin.py, as the Jinja forms do, and is audited. Refused, with the
reason: deactivating yourself, and any change after which nobody active holds
users.manage.
"""
import uuid

import pytest
from sqlalchemy import text

from app.audit.db_models import AuditEventDB
from app.auth import service
from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB, RolePermissionDB, UserDB
from app.auth.permissions import USERS_MANAGE, VIEW
from tests.test_api_guard import signed_in
from tests.test_brand_profile_api import person_with


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    yield session
    session.rollback()
    users = [u for (u,) in session.query(UserDB.id).filter(UserDB.email.like("t358-%"))]
    roles = [r for (r,) in session.query(RoleDB.id).filter(RoleDB.key.like("t358-%"))]
    brands = [b for (b,) in session.query(BrandDB.id).filter(BrandDB.key.like("t358-%"))]
    session.query(AuditEventDB).filter(
        ((AuditEventDB.subject_type == "user") & AuditEventDB.subject_id.in_(users))
        | ((AuditEventDB.subject_type == "role") & AuditEventDB.subject_id.in_(roles))
        | ((AuditEventDB.subject_type == "brand") & AuditEventDB.subject_id.in_(brands))
        | AuditEventDB.brand_id.in_(brands)).delete(synchronize_session=False)
    session.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id.in_(users)
                                           | RoleAssignmentDB.role_id.in_(roles)).delete(synchronize_session=False)
    for uid in users:
        session.execute(text("DELETE FROM auth_sessions WHERE user_id = :u"), {"u": uid})
    session.query(UserDB).filter(UserDB.id.in_(users)).delete(synchronize_session=False)
    session.query(RolePermissionDB).filter(RolePermissionDB.role_id.in_(roles)).delete(synchronize_session=False)
    session.query(RoleDB).filter(RoleDB.id.in_(roles)).delete(synchronize_session=False)
    session.query(BrandDB).filter(BrandDB.id.in_(brands)).delete(synchronize_session=False)
    session.commit()
    session.close()


def _audited(db, action, subject_type, subject_id):
    db.expire_all()
    return db.query(AuditEventDB).filter_by(action=action, subject_type=subject_type, subject_id=subject_id).count()


def _email():
    return f"t358-{uuid.uuid4().hex[:6]}@example.invalid"


# --- who may ---------------------------------------------------------------------------

def test_reading_needs_users_manage_not_only_view(db):
    with person_with(db, [VIEW]) as (client, _headers):
        assert client.get("/auth/users").status_code == 403
        assert client.get("/auth/roles").status_code == 403
    with person_with(db, [VIEW, USERS_MANAGE]) as (client, _headers):
        assert client.get("/auth/users").status_code == 200


# --- people ----------------------------------------------------------------------------

def test_a_person_is_created_granted_and_deactivated_all_audited(db):
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        created = client.post("/auth/users", json={"email": _email(), "display_name": "Tess", "role_key": "viewer"},
                              headers=headers)
        assert created.status_code == 201, created.text
        person = created.json()
        assert [g["role_name"] for g in person["grants"]] == ["Viewer"] or len(person["grants"]) == 1
        again = client.post("/auth/users", json={"email": person["email"]}, headers=headers)
        manager = db.query(RoleDB).filter_by(key="manager").one()
        granted = client.post(f"/auth/users/{person['id']}/grants", json={"role_id": manager.id}, headers=headers)
        grant_id = next(g["id"] for g in granted.json()["grants"] if g["role_id"] == manager.id)
        removed = client.delete(f"/auth/users/{person['id']}/grants/{grant_id}", headers=headers)
        off = client.post(f"/auth/users/{person['id']}/active", json={"active": False}, headers=headers)
    assert again.status_code == 409
    assert manager.id not in {g["role_id"] for g in removed.json()["grants"]}
    assert off.status_code == 200 and off.json()["is_active"] is False
    for action in ("user.created", "user.role_granted", "user.role_revoked", "user.deactivated"):
        assert _audited(db, action, "user", person["id"]) == 1, action


def test_you_cannot_deactivate_yourself(db):
    with signed_in(db) as (client, _token, csrf):
        me = next(p for p in client.get("/auth/users").json() if p["is_you"])
        response = client.post(f"/auth/users/{me['id']}/active", json={"active": False},
                               headers={"X-CSRF-Token": csrf})
    assert response.status_code == 409 and "yourself" in response.text


def test_the_jinja_form_refuses_it_too_and_says_why(db):
    with signed_in(db) as (client, token, csrf):
        me = service.user_for_token(db, token)
        response = client.post(f"/ui/users/{me.id}/active", data={"active": "", "csrf_token": csrf},
                               headers={"X-CSRF-Token": csrf}, follow_redirects=False)
        assert response.status_code == 303 and "error=" in response.headers["location"]
        db.expire_all()
        assert db.get(UserDB, me.id).is_active is True


# --- the lock-out guard ----------------------------------------------------------------

def test_taking_users_manage_off_the_only_role_that_has_it_is_refused(db):
    admin_role = db.query(RoleDB).filter_by(key="admin").one()
    others = {r for (r,) in db.query(RolePermissionDB.role_id).filter(
        RolePermissionDB.permission == USERS_MANAGE, RolePermissionDB.role_id != admin_role.id)}
    if others:
        pytest.skip("another role holds users.manage in this database")
    before = {p for (p,) in db.query(RolePermissionDB.permission).filter_by(role_id=admin_role.id)}
    try:
        with signed_in(db) as (client, _token, csrf):
            response = client.put(f"/auth/roles/{admin_role.id}/permissions",
                                  json={"permissions": sorted(before - {USERS_MANAGE})},
                                  headers={"X-CSRF-Token": csrf})
        assert response.status_code == 409 and "nobody who can manage users" in response.text
        db.expire_all()
        assert USERS_MANAGE in {p for (p,) in db.query(RolePermissionDB.permission).filter_by(role_id=admin_role.id)}
    finally:
        service.set_role_permissions(db, admin_role.id, sorted(before))


def test_who_would_be_left_counts_each_change(db):
    with signed_in(db) as (client, token, _csrf):
        me = service.user_for_token(db, token)
        holders = service.user_managers(db)
        assert me.id in holders
        assert me.id not in service.user_managers(db, without_user=me.id)
        [grant] = db.query(RoleAssignmentDB).filter_by(user_id=me.id).all()
        assert me.id not in service.user_managers(db, without_assignment=grant.id)
        assert me.id not in service.user_managers(db, role_change=(grant.role_id, {VIEW}))


@pytest.mark.parametrize("before, after, refused", [(True, set(), True), (True, {1}, False), (False, set(), False)])
def test_refused_only_when_somebody_could_and_nobody_would(before, after, refused):
    if refused:
        with pytest.raises(service.AccessLockout):
            service._refuse_lockout(None, before, after)
    else:
        service._refuse_lockout(None, before, after)


# --- roles and brands ------------------------------------------------------------------

def test_roles_are_created_edited_and_deleted_all_audited(db):
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        viewer = db.query(RoleDB).filter_by(key="viewer").one()
        role = client.post("/auth/roles", json={"key": f"t358-{uuid.uuid4().hex[:6]}", "name": "Editor",
                                                "copy_from": viewer.id}, headers=headers).json()
        edited = client.put(f"/auth/roles/{role['id']}/permissions", json={"permissions": ["content.manage"]},
                            headers=headers).json()
        builtin = client.delete(f"/auth/roles/{viewer.id}", headers=headers)
        deleted = client.delete(f"/auth/roles/{role['id']}", headers=headers)
        catalogue = {p["key"]: p for p in client.get("/auth/permissions").json()}
    assert edited["permissions"] == ["content.manage", "view"]
    assert builtin.status_code == 409 and deleted.status_code == 204
    assert catalogue["content.manage"]["brand_scoped"] is True and catalogue["users.manage"]["brand_scoped"] is False
    for action in ("role.created", "role.permissions_set", "role.deleted"):
        assert _audited(db, action, "role", role["id"]) == 1, action


def test_brands_are_created_renamed_and_deleted_all_audited(db):
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        brand = client.post("/auth/brands", json={"key": f"t358-{uuid.uuid4().hex[:6]}", "name": "Brand X"},
                            headers=headers).json()
        renamed = client.patch(f"/auth/brands/{brand['id']}", json={"name": "Brand Y"}, headers=headers)
        assert renamed.json()["name"] == "Brand Y"
        assert _audited(db, "brand.renamed", "brand", brand["id"]) == 1
        deleted = client.delete(f"/auth/brands/{brand['id']}", headers=headers)
    assert deleted.status_code == 204
    assert _audited(db, "brand.deleted", "brand", brand["id"]) == 1


def test_deactivating_and_revoking_both_ask_who_would_be_left(db, monkeypatch):
    """The wiring: with a stand-in saying nobody would be left after the
    change, both are refused and nothing changes."""
    with signed_in(db) as (client, token, csrf):
        target = client.post("/auth/users", json={"email": _email(), "role_key": "viewer"},
                             headers={"X-CSRF-Token": csrf}).json()
        grant_id = target["grants"][0]["id"]
        monkeypatch.setattr(service, "user_managers", lambda db, **change: set() if change else {1})
        with pytest.raises(service.AccessLockout):
            service.set_active(db, target["id"], False)
        with pytest.raises(service.AccessLockout):
            service.revoke_assignment(db, grant_id)
        db.expire_all()
        assert db.get(UserDB, target["id"]).is_active is True
        assert db.get(RoleAssignmentDB, grant_id) is not None


def test_integration_managers_read_the_grant_catalogue_without_user_administration(db):
    """task-386: the checklist's permissions come from the integrations API."""
    from app.auth.permissions import INTEGRATIONS_MANAGE

    with person_with(db, [VIEW, INTEGRATIONS_MANAGE]) as (client, _headers):
        response = client.get("/integrations/permissions")
        assert client.get("/auth/permissions").status_code == 403
    assert response.status_code == 200
    assert any(p["key"] == "content.manage" and p["brand_scoped"] for p in response.json())
