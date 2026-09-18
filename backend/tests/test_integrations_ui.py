"""The integration admin screen — ADR-166 stage 4.

ADR-166's Notes call this "the obvious shape of an answer" to the gap point 4
leaves open — a credential outlives the person who issued it — and are careful
to say naming it is not closing it. That is still true: this screen does not
revoke anything when an operator leaves. What it supplies is the thing ADR-151
§5 relies on for people and nothing supplied for machines: somewhere to look.

**The test that matters most is `test_issuing_a_key_does_not_redirect`.** The
idiomatic thing after a POST is a redirect, and the only way to carry a secret
through one is a query string — which is exactly where ADR-166 point 3 forbids
it, because a referrer header, an access log or an intermediary will capture
it. The correct implementation is slightly unidiomatic, so it is the one most
likely to be "tidied up" later.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import service as auth
from app.auth.db_models import (
    IntegrationCredentialDB, IntegrationDB, IntegrationGrantDB, RoleDB,
)
from app.database import SessionLocal
from main import app

TAG = "uitest"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _signed_in(db, role_key):
    user = auth.create_user(
        db, email=f"{TAG}-{uuid.uuid4().hex[:8]}@example.invalid", role_key=role_key,
    )
    token = auth.create_session(db, user)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    return client, user


# Everything that points at a user, in the order the foreign keys demand.
# Kept as one list because a cleanup that misses a table fails only when some
# test happens to create that row — which is exactly the case a mutation run
# produces, since a mutation that disables a guard makes the refused action
# SUCCEED and leave data behind.
_USER_REFERENCES = ("login_codes", "auth_sessions", "role_assignments")


def _purge_users(db, where_sql, params):
    db.rollback()
    subquery = f"(SELECT id FROM users WHERE {where_sql})"
    for table in _USER_REFERENCES:
        db.execute(text(f"DELETE FROM {table} WHERE user_id IN {subquery}"), params)
    db.execute(text(
        f"UPDATE integrations SET created_by_user_id = NULL "
        f"WHERE created_by_user_id IN {subquery}"), params)
    db.execute(text(f"DELETE FROM users WHERE {where_sql}"), params)
    db.commit()


def _cleanup_user(db, user):
    _purge_users(db, "id = :u", {"u": user.id})


def _cleanup_integrations(db):
    db.rollback()
    ids = [r[0] for r in db.execute(text(
        "SELECT id FROM integrations WHERE name LIKE :p"), {"p": f"{TAG}-%"}).all()]
    if ids:
        for model in (IntegrationCredentialDB, IntegrationGrantDB):
            db.query(model).filter(model.integration_id.in_(ids)).delete(
                synchronize_session=False)
        db.query(IntegrationDB).filter(IntegrationDB.id.in_(ids)).delete(
            synchronize_session=False)
        db.commit()


def _csrf(client, path="/ui/integrations"):
    client.get(path)
    # The token is derived from the session, so any authenticated page carries
    # the same one.
    import re
    body = client.get(path).text
    match = re.search(r'name="csrf_token" value="([^"]+)"', body)
    return match.group(1) if match else ""


class TestWhoMayOpenIt:

    def test_an_admin_may(self, db):
        client, user = _signed_in(db, "admin")
        try:
            assert client.get("/ui/integrations").status_code == 200
        finally:
            _cleanup_user(db, user)

    def test_a_manager_may_not(self, db):
        """`integrations.manage` is Admin's by ADR-166 point 4 — and grantable
        to any role a company builds, which is why it is a permission and not a
        hardcoded role check."""
        client, user = _signed_in(db, "manager")
        try:
            assert client.get("/ui/integrations").status_code == 403
        finally:
            _cleanup_user(db, user)


class TestIssuingAKey:

    def test_issuing_a_key_does_not_redirect(self, db):
        """The secret rides in the response body, never through a URL.

        A 303 here would need the secret in a query string, which ADR-166
        point 3 forbids for the same reason it rejected the one-click approve
        link: a bearer credential anything can capture.
        """
        client, user = _signed_in(db, "admin")
        try:
            token = _csrf(client)
            client.post("/ui/integrations", data={
                "csrf_token": token, "name": f"{TAG}-n8n", "description": "",
            })
            integration = db.query(IntegrationDB).filter(
                IntegrationDB.name == f"{TAG}-n8n").first()
            assert integration is not None

            response = client.post(
                f"/ui/integrations/{integration.id}/keys",
                data={"csrf_token": token, "label": "primary"},
            )
            assert response.status_code == 200, "a redirect would need a query string"
            assert "nri_" in response.text

            # And the thing shown is not what is stored.
            credential = db.query(IntegrationCredentialDB).filter(
                IntegrationCredentialDB.integration_id == integration.id).first()
            assert credential.secret_hash not in response.text
        finally:
            _cleanup_integrations(db)
            _cleanup_user(db, user)

    def test_a_key_can_be_revoked_from_the_screen(self, db):
        from app.auth import integrations as ints

        client, user = _signed_in(db, "admin")
        try:
            integration = ints.create_integration(db, name=f"{TAG}-revoke")
            credential, _ = ints.issue_credential(db, integration.id)
            token = _csrf(client)

            response = client.post(
                f"/ui/integrations/{integration.id}/keys/{credential.id}/revoke",
                data={"csrf_token": token},
            )
            assert response.status_code == 303
            db.refresh(credential)
            assert credential.revoked_at is not None
        finally:
            _cleanup_integrations(db)
            _cleanup_user(db, user)


class TestCsrfNowCoversTheAdminForms:
    """Found while building this screen, and fixed with it.

    `enforce_csrf` was wired onto the frontend router alone, so the thirteen
    user- and role-administration forms in `auth_router` — the most privileged
    in the system — were the only ones with no CSRF protection, while launch
    gate 4 recorded "CSRF on all 62 forms".
    """

    def test_a_user_admin_post_without_a_token_is_refused(self, db):
        client, user = _signed_in(db, "admin")
        try:
            response = client.post("/ui/users", data={
                "email": f"{TAG}-csrf-{uuid.uuid4().hex[:6]}@example.invalid",
                "role_key": "viewer",
            })
            assert response.status_code == 403
        finally:
            # FK order, and it matters more than it looks: a mutation run that
            # switches this guard off makes the POST SUCCEED, which creates a
            # real user with a role assignment. The cleanup has to survive the
            # case the test exists to detect.
            # A mutation run that switches this guard off makes the POST
            # SUCCEED, which creates a real user with a role assignment. The
            # cleanup has to survive the case the test exists to detect.
            _purge_users(db, "email LIKE :p", {"p": f"{TAG}-csrf-%"})
            _cleanup_user(db, user)

    def test_signing_in_still_works_without_a_session(self):
        """`enforce_csrf` skips a request with no session cookie, which is what
        an anonymous sign-in POST is. Guarding the router must not lock the
        front door."""
        anonymous = TestClient(app, follow_redirects=False,
                               raise_server_exceptions=False)
        response = anonymous.post("/ui/login", data={"email": "nobody@example.invalid"})
        assert response.status_code != 403
