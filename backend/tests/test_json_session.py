"""Signing in over JSON — ADR-168's missing entry point.

ADR-168 decided the manager client authenticates with the session cookie, and
the only way to obtain one was an HTML form answering with a 303 to a page. A
client that renders its own screens cannot follow that, so the decision had no
door. Found 2026-09-19 while auditing what the JSON API cannot do.

**The tests that matter are the neutrality ones.** These routes are siblings of
the form routes, and the property gate 4b was opened to fix — one answer for a
known address, an unknown one, a deactivated user and a failed send — has to
hold identically here. A JSON surface makes it harder rather than easier: a
redirect says nothing by construction, while a body has to be written to say
nothing, and every branch is a chance to say something.

Runs against the isolated test database and removes what it creates.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import service as auth
from app.auth.db_models import LoginCodeDB, UserDB
from app.database import SessionLocal
from main import app

TAG = "jsonsession"
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user(db):
    created = auth.create_user(
        db, email=f"{TAG}-{uuid.uuid4().hex[:8]}@example.invalid", role_key="manager",
    )
    try:
        yield created
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": created.id})
        db.execute(text("DELETE FROM audit_events WHERE actor_id = :u"), {"u": created.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": created.id})
        db.commit()


def _latest_code(db, user_id):
    """The code as the server stored it — hashed, so it cannot be read back.

    Tests mint their own rather than reading the log, which is where the real
    code goes. `verify_login_code` compares the hash, so writing a known code's
    hash is the same operation the request route performs.
    """
    row = db.query(LoginCodeDB).filter(
        LoginCodeDB.user_id == user_id
    ).order_by(LoginCodeDB.id.desc()).first()
    return row


class TestTheAnswerIsAlwaysTheSame:
    """ADR-151 §2, on a surface that cannot redirect its way out of saying
    something."""

    @pytest.mark.parametrize("case", ["known", "unknown", "deactivated", "malformed"])
    def test_requesting_a_code_answers_identically(self, db, user, case):
        addresses = {
            "known": user.email,
            "unknown": f"{TAG}-nobody-{uuid.uuid4().hex[:8]}@example.invalid",
            "deactivated": user.email,
            "malformed": "not-an-address",
        }
        if case == "deactivated":
            auth.set_active(db, user.id, False)

        response = client.post(
            "/auth/session/request", json={"email": addresses[case]},
        )

        assert response.status_code == 202, case
        assert response.json() == {
            "status": "code_requested",
            "detail": (
                "If that address belongs to an active account, a sign-in code "
                "is on its way. Submit it to /auth/session/verify."
            ),
        }, case

    def test_no_code_is_ever_returned(self, db, user):
        """The defect gate 4b closed: a live code in the response body.

        `request_login_code` still RETURNS one — the dev path needs it for the
        log — so the guarantee is that this route drops it, and that is the
        line a refactor would quietly undo.
        """
        response = client.post("/auth/session/request", json={"email": user.email})

        body = response.text
        code = _latest_code(db, user.id)
        assert code is not None, "a known address should have produced a code"
        assert code.code_hash not in body
        for key in ("code", "dev_code", "token"):
            assert key not in response.json()

    @pytest.mark.parametrize("case", ["wrong_code", "unknown_address", "no_code_asked"])
    def test_every_verification_failure_answers_identically(self, db, user, case):
        """A wrong code, an address with no outstanding code, and an address
        with no account must be indistinguishable. Naming which part was wrong
        is the oracle in a different costume."""
        client.post("/auth/session/request", json={"email": user.email})
        attempts = {
            "wrong_code": {"email": user.email, "code": "000000"},
            "unknown_address": {
                "email": f"{TAG}-nobody-{uuid.uuid4().hex[:8]}@example.invalid",
                "code": "123456",
            },
            "no_code_asked": {"email": user.email, "code": "999999"},
        }

        response = client.post("/auth/session/verify", json=attempts[case])

        assert response.status_code == 401, case
        assert response.json()["detail"] == "That code is not valid or has expired.", case


class TestSigningInWorks:

    def _sign_in(self, db, user):
        """Mint a code the way the server would, then exchange it."""
        import hashlib

        client.post("/auth/session/request", json={"email": user.email})
        row = _latest_code(db, user.id)
        code = "424242"
        row.code_hash = hashlib.sha256(code.encode()).hexdigest()
        db.commit()
        return client.post(
            "/auth/session/verify", json={"email": user.email, "code": code},
        )

    def test_a_valid_code_returns_a_session_and_a_csrf_token(self, db, user):
        response = self._sign_in(db, user)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "signed_in"
        assert body["user"]["email"] == user.email
        assert body["csrf_token"], (
            "the SPA cannot write without it, and the only moment it can be "
            "learned is the moment the session is created"
        )
        assert auth.SESSION_COOKIE in response.cookies

    def test_the_cookie_carries_the_same_attributes_as_the_form_route(self, db, user):
        response = self._sign_in(db, user)

        header = response.headers["set-cookie"]
        assert "HttpOnly" in header, "script must not be able to read it"
        assert "SameSite=lax" in header.lower() or "samesite=lax" in header.lower(), (
            "ADR-168 point 3's same-origin requirement is what keeps lax viable"
        )

    def test_the_returned_csrf_token_actually_works(self, db, user):
        """End to end: sign in over JSON, then make a JSON write with the token
        that sign-in handed back. This is the whole point of the route pair."""
        signed = self._sign_in(db, user)
        token = signed.json()["csrf_token"]

        authed = TestClient(app, raise_server_exceptions=False)
        authed.cookies.set(auth.SESSION_COOKIE, signed.cookies[auth.SESSION_COOKIE])
        response = authed.post(
            "/content/",
            json={
                "brand_id": auth.ensure_default_brand(db).id,
                "title": f"{TAG}-{uuid.uuid4().hex[:8]}",
                "content_type": "cms",
                "content": {"headline": "x", "body_medium": "y"},
            },
            headers={"X-CSRF-Token": token},
        )

        assert response.status_code in (200, 201), response.text
        db.execute(text("DELETE FROM content_records WHERE id = :i"),
                   {"i": response.json()["id"]})
        db.commit()

    def test_a_sign_in_is_audited(self, db, user):
        from app.audit.db_models import AuditEventDB

        self._sign_in(db, user)

        events = db.query(AuditEventDB).filter(
            AuditEventDB.actor_id == user.id,
            AuditEventDB.action == "user.signed_in",
        ).all()
        assert events, (
            "ADR-153 point 2: a sign-in has no domain record, so an unaudited "
            "one is simply not recorded anywhere"
        )


class TestSigningOut:

    def test_it_revokes_the_session(self, db, user):
        import hashlib

        client.post("/auth/session/request", json={"email": user.email})
        row = _latest_code(db, user.id)
        row.code_hash = hashlib.sha256(b"424242").hexdigest()
        db.commit()
        signed = client.post(
            "/auth/session/verify", json={"email": user.email, "code": "424242"},
        )
        token = signed.cookies[auth.SESSION_COOKIE]
        assert auth.user_for_token(db, token) is not None

        out = TestClient(app, raise_server_exceptions=False)
        out.cookies.set(auth.SESSION_COOKIE, token)
        response = out.post(
            "/auth/session", headers={"X-CSRF-Token": auth.csrf_token_for(token)},
        )

        assert response.status_code == 204
        assert auth.user_for_token(db, token) is None, "the session survived sign-out"

    def test_it_needs_a_csrf_token(self, db, user):
        """**The bug this router placement avoided.**

        Sign-out is the one session route that carries a cookie, so it is the
        one that needs CSRF — and it is why these routes are not on
        `auth_router`, whose form-borne guard would read a JSON body as an
        empty FormData and refuse every call.
        """
        import hashlib

        client.post("/auth/session/request", json={"email": user.email})
        row = _latest_code(db, user.id)
        row.code_hash = hashlib.sha256(b"424242").hexdigest()
        db.commit()
        signed = client.post(
            "/auth/session/verify", json={"email": user.email, "code": "424242"},
        )
        token = signed.cookies[auth.SESSION_COOKIE]

        out = TestClient(app, raise_server_exceptions=False)
        out.cookies.set(auth.SESSION_COOKIE, token)
        response = out.post("/auth/session")

        assert response.status_code == 403
        assert auth.user_for_token(db, token) is not None, (
            "a CSRF-less sign-out revoked the session anyway"
        )


class TestTheTokenSurvivesAReload:
    """**The blocker nobody had written down.**

    `/auth/session/verify` hands the CSRF token over exactly once, at the moment
    the session is created. Everything else about the session is in an
    `httponly` cookie the SPA cannot read, so a browser that reloaded the page,
    opened a second tab or restored a session held a valid session and no token
    — and could not perform a single write until it signed out and back in.

    Found 2026-09-20 while planning the React client. The screen inventory lists
    three gaps blocking the first screen; this was a fourth, in the auth spine
    itself. `GET /auth/session` now answers with the token, which costs no round
    trip because the shell calls that route on every load anyway.

    These tests are the fix's only guard: nothing else would notice if the field
    were dropped, and the failure would look like a permissions bug.
    """

    def _sign_in_and_forget_the_token(self, db, user):
        """Sign in, then keep **only the cookie** — exactly what a browser has
        after the page is reloaded."""
        import hashlib

        client.post("/auth/session/request", json={"email": user.email})
        row = _latest_code(db, user.id)
        row.code_hash = hashlib.sha256(b"424242").hexdigest()
        db.commit()
        signed = client.post(
            "/auth/session/verify", json={"email": user.email, "code": "424242"},
        )
        assert signed.status_code == 200, signed.text

        reloaded = TestClient(app, raise_server_exceptions=False)
        reloaded.cookies.set(auth.SESSION_COOKIE, signed.cookies[auth.SESSION_COOKIE])
        return reloaded

    def test_the_context_route_hands_back_a_csrf_token(self, db, user):
        reloaded = self._sign_in_and_forget_the_token(db, user)

        response = reloaded.get("/auth/session")

        assert response.status_code == 200, response.text
        assert response.json()["csrf_token"], (
            "a reloaded SPA has the cookie and nothing else — without this it "
            "cannot write at all"
        )

    def test_that_token_actually_authorises_a_write(self, db, user):
        """End to end, and the half that matters: a token that is returned but
        does not work would pass the test above."""
        reloaded = self._sign_in_and_forget_the_token(db, user)
        token = reloaded.get("/auth/session").json()["csrf_token"]

        response = reloaded.post(
            "/content/",
            json={
                "brand_id": auth.ensure_default_brand(db).id,
                "title": f"{TAG}-{uuid.uuid4().hex[:8]}",
                "content_type": "cms",
                "content": {"headline": "x", "body_medium": "y"},
            },
            headers={"X-CSRF-Token": token},
        )

        assert response.status_code in (200, 201), response.text
        db.execute(text("DELETE FROM content_records WHERE id = :i"),
                   {"i": response.json()["id"]})
        db.commit()

    def test_the_response_is_not_cacheable(self, db, user):
        """It carries a per-session secret, so a shared cache holding it would
        hand one person's token to another."""
        reloaded = self._sign_in_and_forget_the_token(db, user)

        response = reloaded.get("/auth/session")

        assert response.headers.get("cache-control") == "no-store", (
            "a response carrying a CSRF token must not be cacheable"
        )


class TestAStaleCookieDoesNotLockYouOut:
    """**The deadlock, found by a user who simply could not sign in.**

    `enforce_api_csrf` skipped only when there was no cookie *string*. A browser
    holding a revoked or expired `nra_session` — from a signed-out tab, an idle
    timeout, or the Jinja UI — still sent one, so CSRF was enforced against a
    session that no longer existed.

    The SPA could not satisfy it. `GET /auth/session` answered 401, so it never
    received a token, and the cookie is `httponly` so it could neither read nor
    clear one. Every write refused with 403 **including the sign-in routes**, so
    the only escape was deleting the cookie by hand in developer tools. The
    symptom reported was "401 and 403, no code in the terminal, no code screen"
    — no code, because the request never reached the service.

    The Jinja plane never had this, which is why nobody hit it earlier: its
    template renders a token derived server-side from whatever cookie is
    present, so a stale cookie still produces a matching one.
    """

    def test_an_unknown_cookie_does_not_block_asking_for_a_code(self, db, user):
        blocked = TestClient(app, raise_server_exceptions=False)
        blocked.cookies.set(auth.SESSION_COOKIE, "not-a-real-session-token")

        response = blocked.post("/auth/session/request", json={"email": user.email})

        assert response.status_code == 202, (
            "a cookie that resolves to nothing is not a session, and treating "
            "it as one makes signing in impossible from the client"
        )

    def test_a_revoked_session_does_not_block_signing_in_again(self, db, user):
        """The realistic version: signed out in another tab, then sign in here.

        The session is minted directly rather than through the code flow --
        these tests only need a cookie, and requesting a code per test walks
        into the per-client sign-in throttle.
        """
        token = auth.create_session(db, user)
        auth.revoke_token(db, token)

        stale = TestClient(app, raise_server_exceptions=False)
        stale.cookies.set(auth.SESSION_COOKIE, token)
        response = stale.post("/auth/session/request", json={"email": user.email})

        assert response.status_code == 202

    def test_a_live_session_still_needs_its_token(self, db, user):
        """**The other half, and the one that must not regress.**

        Skipping CSRF for a dead session is correct; skipping it for a live one
        would remove the control ADR-168 point 2 exists to add.
        """
        token = auth.create_session(db, user)

        live = TestClient(app, raise_server_exceptions=False)
        live.cookies.set(auth.SESSION_COOKIE, token)
        response = live.post("/auth/session")  # sign out, a write, no header

        assert response.status_code == 403
        assert auth.user_for_token(db, token) is not None

    def test_asking_does_not_extend_the_session(self, db, user):
        """`session_is_live` must not touch `last_seen_at`.

        The guard runs on every write. If asking whether a session exists also
        kept it alive, the idle timeout would stop meaning anything -- and it
        would add a sixth write per request to an already-logged write
        amplification defect.
        """
        from app.auth.db_models import SessionDB

        token = auth.create_session(db, user)
        session_row = db.query(SessionDB).filter(
            SessionDB.token_hash == auth.hash_secret(token)
        ).first()
        before = session_row.last_seen_at

        assert auth.session_is_live(db, token) is True

        db.refresh(session_row)
        assert session_row.last_seen_at == before, "the read-only check wrote"
