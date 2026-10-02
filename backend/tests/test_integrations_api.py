"""Managing integrations over JSON (task-50, C14; ADR-166 addendum 2026-10-02).

Two rules carry the weight and each has a test that fails without it:
  - PEOPLE ONLY — a bearer credential is refused even when it holds
    `integrations.manage`, because a machine that can mint credentials can mint
    itself any grant;
  - NO ESCALATION — a person grants only what they hold, on that brand.
And the secret appears once: in the issue-key response, `no-store`, never again.
"""
import re
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import integrations as ints
from app.auth import service as auth
from app.auth.db_models import (
    IntegrationCredentialDB, IntegrationDB, IntegrationGrantDB,
    RoleAssignmentDB, RoleDB, RolePermissionDB,
)
from app.auth.permissions import (
    INTEGRATIONS_MANAGE, SENDS_EXECUTE, VIEW,
)
from app.database import SessionLocal
from main import app
from tests.machine import machine
from tests.test_api_guard import signed_in

client = TestClient(app, raise_server_exceptions=False)
TAG = "intapi"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _purge(db):
    db.rollback()
    ids = [i.id for i in db.query(IntegrationDB).filter(IntegrationDB.name.like(f"{TAG}-%")).all()]
    if ids:
        from app.audit.db_models import AuditEventDB

        db.query(AuditEventDB).filter(
            AuditEventDB.subject_type == "integration",
            AuditEventDB.subject_id.in_(ids)).delete(synchronize_session=False)
        db.query(IntegrationCredentialDB).filter(
            IntegrationCredentialDB.integration_id.in_(ids)).delete(synchronize_session=False)
        db.query(IntegrationGrantDB).filter(
            IntegrationGrantDB.integration_id.in_(ids)).delete(synchronize_session=False)
        db.query(IntegrationDB).filter(IntegrationDB.id.in_(ids)).delete(synchronize_session=False)
        db.commit()


@pytest.fixture
def made(db):
    """Safety net: integrations a test created, removed afterwards."""
    yield
    _purge(db)


@contextmanager
def signed_in_admin(db):
    """`signed_in`, but integrations the admin created go first — the user row
    cannot be deleted while `integrations.created_by_user_id` points at it."""
    with signed_in(db) as session:
        try:
            yield session
        finally:
            _purge(db)


def _name():
    return f"{TAG}-{uuid.uuid4().hex[:8]}"


def _create(cookied, csrf, name=None):
    response = cookied.post("/integrations", json={"name": name or _name()},
                            headers={"X-CSRF-Token": csrf})
    assert response.status_code == 201, response.text
    return response.json()


class TestPeopleOnly:
    def test_a_machine_holding_the_permission_is_refused_everywhere(self, db, made):
        with machine([VIEW, INTEGRATIONS_MANAGE]) as headers:
            listing = client.get("/integrations", headers=headers)
            created = client.post("/integrations", json={"name": _name()}, headers=headers)

        assert listing.status_code == 403, listing.text
        assert created.status_code == 403, created.text
        assert "person" in created.json()["detail"].lower() or "machine" in created.json()["detail"].lower()
        assert db.query(IntegrationDB).filter(IntegrationDB.name.like(f"{TAG}-%")).count() == 0

    def test_a_machine_cannot_mint_a_key_for_itself(self, db, made):
        with signed_in_admin(db) as (cookied, _t, csrf):
            integration = _create(cookied, csrf)
        with machine([VIEW, INTEGRATIONS_MANAGE]) as headers:
            response = client.post(f"/integrations/{integration['id']}/keys",
                                   json={"label": "x"}, headers=headers)
        assert response.status_code == 403, response.text
        assert db.query(IntegrationCredentialDB).filter(
            IntegrationCredentialDB.integration_id == integration["id"]).count() == 0


class TestWhoMayManage:
    def test_a_viewer_cannot_even_read_the_list(self, db, made):
        """The GET trap: the policy table answers `view` for every GET."""
        with signed_in(db, role_key="viewer") as (cookied, _t, _c):
            assert cookied.get("/integrations").status_code == 403

    def test_a_manager_cannot_manage_integrations(self, db, made):
        with signed_in(db, role_key="manager") as (cookied, _t, csrf):
            assert cookied.get("/integrations").status_code == 403
            assert cookied.post("/integrations", json={"name": _name()},
                                headers={"X-CSRF-Token": csrf}).status_code == 403

    def test_an_admin_can(self, db, made):
        with signed_in_admin(db) as (cookied, _t, csrf):
            integration = _create(cookied, csrf)
            listing = cookied.get("/integrations").json()
        assert integration["id"] in [i["id"] for i in listing]
        assert integration["created_by_user_id"] is not None


class TestTheSecretIsShownOnce:
    def test_issue_returns_it_with_no_store_and_nothing_else_does(self, db, made):
        with signed_in_admin(db) as (cookied, _t, csrf):
            integration = _create(cookied, csrf)
            issued = cookied.post(f"/integrations/{integration['id']}/keys",
                                  json={"label": "n8n"}, headers={"X-CSRF-Token": csrf})
            assert issued.status_code == 201, issued.text
            body = issued.json()
            secret_key = body["secret_key"]
            assert issued.headers["cache-control"] == "no-store"
            key_id, secret = secret_key.split(".", 1)
            assert key_id == body["credential"]["key_id"] and len(secret) >= 32

            # Everything that reads it back is silent about the secret and hash.
            listing = cookied.get("/integrations")
            row = db.query(IntegrationCredentialDB).filter(
                IntegrationCredentialDB.key_id == key_id).one()
            assert secret not in listing.text
            assert row.secret_hash not in listing.text
            assert "secret" not in listing.text.lower().replace("secret_key", "")

            # And it is the real credential.
            assert ints.authenticate(db, key_id, secret) is not None

    def test_a_deactivated_integration_issues_nothing(self, db, made):
        with signed_in_admin(db) as (cookied, _t, csrf):
            integration = _create(cookied, csrf)
            h = {"X-CSRF-Token": csrf}
            assert cookied.post(f"/integrations/{integration['id']}/deactivate", headers=h).status_code == 200
            response = cookied.post(f"/integrations/{integration['id']}/keys", json={}, headers=h)
        assert response.status_code == 409


class TestRevocation:
    def test_a_key_is_revoked_only_through_its_own_integration(self, db, made):
        with signed_in_admin(db) as (cookied, _t, csrf):
            h = {"X-CSRF-Token": csrf}
            one, two = _create(cookied, csrf), _create(cookied, csrf)
            issued = cookied.post(f"/integrations/{one['id']}/keys", json={}, headers=h).json()
            credential_id = issued["credential"]["id"]
            key_id, secret = issued["secret_key"].split(".", 1)

            wrong = cookied.post(f"/integrations/{two['id']}/keys/{credential_id}/revoke", headers=h)
            assert wrong.status_code == 404, "another integration's route revoked this key"
            assert ints.authenticate(db, key_id, secret) is not None

            right = cookied.post(f"/integrations/{one['id']}/keys/{credential_id}/revoke", headers=h)
            assert right.status_code == 200 and right.json()["live_keys"] == 0
        db.expire_all()
        assert ints.authenticate(db, key_id, secret) is None


class TestNoEscalation:
    @contextmanager
    def _person_holding(self, db, permissions, brand):
        """A person whose only role carries `permissions` on `brand`."""
        role = auth.create_role(db, key=f"{TAG}-{uuid.uuid4().hex[:6]}", name="intapi role")
        auth.set_role_permissions(db, role.id, permissions)
        user = auth.create_user(
            db, email=f"{TAG}-{uuid.uuid4().hex[:8]}@example.invalid", role_key=role.key,
            brand_id=brand.id,
        )
        token = auth.create_session(db, user)
        cookied = TestClient(app, raise_server_exceptions=False)
        cookied.cookies.set(auth.SESSION_COOKIE, token)
        try:
            yield cookied, auth.csrf_token_for(token), token
        finally:
            db.rollback()
            for table in ("login_codes", "auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role.id).delete()
            db.query(RoleDB).filter(RoleDB.id == role.id).delete()
            db.commit()

    def test_a_person_cannot_grant_what_they_do_not_hold(self, db, made, default_brand):
        with signed_in_admin(db) as (admin, _t, admin_csrf), self._person_holding(
            db, [VIEW, INTEGRATIONS_MANAGE], default_brand
        ) as (c, csrf, _tok):
            integration = _create(admin, admin_csrf)
            refused = c.post(f"/integrations/{integration['id']}/grants",
                             json={"permission": SENDS_EXECUTE, "brand_id": default_brand.id},
                             headers={"X-CSRF-Token": csrf})
            allowed = c.post(f"/integrations/{integration['id']}/grants",
                             json={"permission": VIEW, "brand_id": default_brand.id},
                             headers={"X-CSRF-Token": csrf})
        assert refused.status_code == 403, refused.text
        assert allowed.status_code == 201, allowed.text
        assert [g["permission"] for g in allowed.json()["grants"]] == [VIEW]

    def test_a_person_cannot_grant_on_a_brand_they_hold_nothing_on(
        self, db, made, default_brand, temp_brand
    ):
        other = temp_brand()
        with signed_in_admin(db) as (admin, _t, csrf):  # Admin on the DEFAULT brand only
            integration = _create(admin, csrf)
            h = {"X-CSRF-Token": csrf}
            on_other = admin.post(f"/integrations/{integration['id']}/grants",
                                  json={"permission": VIEW, "brand_id": other.id}, headers=h)
            on_missing = admin.post(f"/integrations/{integration['id']}/grants",
                                    json={"permission": VIEW, "brand_id": 99999999}, headers=h)
            on_own = admin.post(f"/integrations/{integration['id']}/grants",
                                json={"permission": VIEW, "brand_id": default_brand.id}, headers=h)
            assert on_other.status_code == on_missing.status_code == 403
            assert on_other.json() == on_missing.json(), "the answer must not say which brands exist"
            assert on_own.status_code == 201
            assert db.query(IntegrationGrantDB).filter(
                IntegrationGrantDB.integration_id == integration["id"],
                IntegrationGrantDB.brand_id == other.id).count() == 0

    def test_the_jinja_page_is_held_to_the_same_rule(self, db, made, default_brand):
        with signed_in_admin(db) as (admin, _t, admin_csrf), self._person_holding(
            db, [VIEW, INTEGRATIONS_MANAGE], default_brand
        ) as (c, _csrf, token):
            integration = _create(admin, admin_csrf)
            c.follow_redirects = False
            response = c.post(
                f"/ui/integrations/{integration['id']}/grants",
                data={"permission": SENDS_EXECUTE, "brand_id": str(default_brand.id),
                      "csrf_token": auth.csrf_token_for(token)},
            )
            assert response.status_code == 303 and "error=" in response.headers["location"], response.text
            assert db.query(IntegrationGrantDB).filter(
                IntegrationGrantDB.integration_id == integration["id"]).count() == 0

    def test_an_unknown_permission_is_422_and_removal_works(self, db, made, default_brand):
        with signed_in_admin(db) as (admin, _t, csrf):
            h = {"X-CSRF-Token": csrf}
            integration = _create(admin, csrf)
            bad = admin.post(f"/integrations/{integration['id']}/grants",
                             json={"permission": "root.everything", "brand_id": default_brand.id}, headers=h)
            assert bad.status_code == 422
            admin.post(f"/integrations/{integration['id']}/grants",
                       json={"permission": VIEW, "brand_id": default_brand.id}, headers=h)
            removed = admin.delete(f"/integrations/{integration['id']}/grants/{VIEW}/{default_brand.id}", headers=h)
            gone = admin.delete(f"/integrations/{integration['id']}/grants/{VIEW}/{default_brand.id}", headers=h)
        assert removed.status_code == 200 and removed.json()["grants"] == []
        assert gone.status_code == 404


class TestUnattended:
    def test_it_can_be_switched_and_is_reported(self, db, made):
        with signed_in_admin(db) as (admin, _t, csrf):
            h = {"X-CSRF-Token": csrf}
            integration = _create(admin, csrf)
            assert integration["may_send_unattended"] is False
            on = admin.put(f"/integrations/{integration['id']}/unattended", json={"allowed": True}, headers=h)
            off = admin.put(f"/integrations/{integration['id']}/unattended", json={"allowed": False}, headers=h)
        assert on.json()["may_send_unattended"] is True
        assert off.json()["may_send_unattended"] is False


class TestNoEscalationThroughUse:
    """The second half of the rule, found by review on 2026-10-02.

    `integrations.manage` is platform-level, so an Admin of the default brand
    only could otherwise mint a key for an integration somebody gave
    `sends.execute` on another brand — and send there. Issuing a key and
    enabling unattended sending need every grant the integration holds;
    removing a grant needs that grant. Each test sets the grant up directly
    with `ints.grant`, standing in for the other brand's own Admin.
    """

    @pytest.fixture
    def foreign_powered(self, db, made, temp_brand):
        other = temp_brand("powered")
        integration = ints.create_integration(db, name=_name())
        assert ints.grant(db, integration.id, SENDS_EXECUTE, other.id)
        return integration, other

    def _keys(self, db, integration_id):
        db.expire_all()
        return db.query(IntegrationCredentialDB).filter(
            IntegrationCredentialDB.integration_id == integration_id).count()

    def test_a_key_is_refused_to_someone_without_the_integrations_power(
        self, db, foreign_powered
    ):
        integration, _other = foreign_powered
        with signed_in_admin(db) as (admin, _t, csrf):  # Admin on the default brand only
            response = admin.post(f"/integrations/{integration.id}/keys", json={},
                                  headers={"X-CSRF-Token": csrf})
            assert response.status_code == 403, response.text
            assert "secret_key" not in response.text
            assert self._keys(db, integration.id) == 0

    def test_the_same_request_succeeds_for_someone_holding_it(self, db, foreign_powered):
        """Without this, the refusal above could be refusing everybody."""
        integration, other = foreign_powered
        with signed_in_admin(db) as (admin, token, csrf):
            user = auth.user_for_token(db, token)
            role = db.query(RoleDB).filter(RoleDB.key == "admin").one()
            db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=other.id))
            db.commit()
            response = admin.post(f"/integrations/{integration.id}/keys", json={},
                                  headers={"X-CSRF-Token": csrf})
            assert response.status_code == 201, response.text
            assert self._keys(db, integration.id) == 1

    def test_the_jinja_page_refuses_the_key_too(self, db, foreign_powered):
        integration, _other = foreign_powered
        with signed_in_admin(db) as (admin, token, _csrf):
            admin.follow_redirects = False
            response = admin.post(f"/ui/integrations/{integration.id}/keys",
                                  data={"label": "x", "csrf_token": auth.csrf_token_for(token)})
            assert response.status_code == 303 and "error=" in response.headers["location"]
            assert self._keys(db, integration.id) == 0

    def test_unattended_sending_cannot_be_switched_on_but_can_be_off(self, db, foreign_powered):
        integration, _other = foreign_powered
        with signed_in_admin(db) as (admin, _t, csrf):
            h = {"X-CSRF-Token": csrf}
            on = admin.put(f"/integrations/{integration.id}/unattended", json={"allowed": True}, headers=h)
            assert on.status_code == 403, on.text
            db.expire_all()
            assert db.get(IntegrationDB, integration.id).may_send_unattended is False
            # Taking power away is never gated.
            off = admin.put(f"/integrations/{integration.id}/unattended", json={"allowed": False}, headers=h)
            assert off.status_code == 200, off.text

    def test_another_brands_grant_cannot_be_removed(self, db, foreign_powered):
        integration, other = foreign_powered
        with signed_in_admin(db) as (admin, _t, csrf):
            response = admin.delete(
                f"/integrations/{integration.id}/grants/{SENDS_EXECUTE}/{other.id}",
                headers={"X-CSRF-Token": csrf})
            assert response.status_code == 403, response.text
            db.expire_all()
            assert db.query(IntegrationGrantDB).filter(
                IntegrationGrantDB.integration_id == integration.id).count() == 1


class TestEveryChangeIsAudited:
    """Until 2026-10-02 integration changes left only a log line. ADR-166
    point 5 calls logging the unattended switch "the whole control"; a log
    line nobody keeps is not one. The secret is never in the entry."""

    def _entries(self, db, integration_id):
        from app.audit.db_models import AuditEventDB

        db.expire_all()
        return db.query(AuditEventDB).filter(
            AuditEventDB.subject_type == "integration",
            AuditEventDB.subject_id == integration_id,
        ).order_by(AuditEventDB.id).all()

    def test_the_json_lifecycle_is_recorded_with_the_person_as_actor(
        self, db, made, default_brand
    ):
        with signed_in_admin(db) as (admin, token, csrf):
            h = {"X-CSRF-Token": csrf}
            user = auth.user_for_token(db, token)
            integration = _create(admin, csrf)
            iid = integration["id"]
            admin.post(f"/integrations/{iid}/grants",
                       json={"permission": VIEW, "brand_id": default_brand.id}, headers=h)
            issued = admin.post(f"/integrations/{iid}/keys", json={"label": "k"}, headers=h).json()
            admin.post(f"/integrations/{iid}/keys/{issued['credential']['id']}/revoke", headers=h)
            admin.put(f"/integrations/{iid}/unattended", json={"allowed": True}, headers=h)
            admin.delete(f"/integrations/{iid}/grants/{VIEW}/{default_brand.id}", headers=h)
            admin.post(f"/integrations/{iid}/deactivate", headers=h)

            entries = self._entries(db, iid)
            assert [e.action for e in entries] == [
                "integration.created", "integration.grant_added", "integration.key_issued",
                "integration.key_revoked", "integration.unattended_set",
                "integration.grant_removed", "integration.deactivated",
            ]
            assert {(e.actor_type, e.actor_id) for e in entries} == {("user", user.id)}
            secret = issued["secret_key"].split(".", 1)[1]
            assert all(secret not in str(e.detail) for e in entries)
            assert entries[1].brand_id == default_brand.id

    def test_the_jinja_grant_is_recorded_too(self, db, made, default_brand):
        with signed_in_admin(db) as (admin, token, csrf):
            integration = _create(admin, csrf)
            admin.follow_redirects = False
            admin.post(f"/ui/integrations/{integration['id']}/grants",
                       data={"permission": VIEW, "brand_id": str(default_brand.id),
                             "csrf_token": auth.csrf_token_for(token)})
            actions = [e.action for e in self._entries(db, integration["id"])]
            assert "integration.grant_added" in actions, actions
