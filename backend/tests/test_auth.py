"""Tests for the access model and passwordless sign-in (ADR-150 / ADR-151).

Runs against the real database, like the other integration tests here, but
every test creates and removes its own users so it leaves the shared dev
database exactly as it found it — these tests must not depend on, or disturb,
whatever the operator is currently building.
"""
import uuid
from datetime import timedelta

import pytest

from app.auth import service as auth
from app.auth.db_models import (
    LoginCodeDB, LoginCodeRequestDB, RoleAssignmentDB, RoleDB, RolePermissionDB,
    SessionDB, UserDB,
)
from app.auth.permissions import (
    ADMIN, AI_RUN, CREDENTIALS_MANAGE, MANAGER, USERS_MANAGE, VIEW, VIEWER,
)
from app.database import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


#: Starlette's TestClient presents this as the peer address.
TEST_CLIENT_HOST = "testclient"


@pytest.fixture(autouse=True)
def clear_test_client_throttle():
    """Keep the request-rate counters from leaking between suite runs.

    Every HTTP test here posts to /ui/login from the same peer address, and
    those requests are now counted against the per-client limit for an hour
    (ADR-151 §2). Left alone, a handful of consecutive suite runs would
    exhaust that bucket and the *oracle* tests — which need a code to actually
    be issued — would start failing for a reason that has nothing to do with
    what they assert.

    Scoped to the test client's own bucket on purpose. Clearing the table
    wholesale would wipe the live counters of whoever is using the dev
    database at the time, which is exactly the kind of "cleanup" that is
    really a security hole.
    """
    def clear():
        with SessionLocal() as session:
            session.query(LoginCodeRequestDB).filter(
                LoginCodeRequestDB.client_hash == auth.hash_secret(TEST_CLIENT_HOST)
            ).delete(synchronize_session=False)
            session.commit()

    clear()
    yield
    clear()


@pytest.fixture
def throttle_ip(db):
    """A client address nobody else is counting against."""
    address = f"198.51.100.{uuid.uuid4().int % 250 + 1}-{uuid.uuid4().hex[:8]}"
    yield address
    db.query(LoginCodeRequestDB).filter(
        LoginCodeRequestDB.client_hash == auth.hash_secret(address)
    ).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def temp_user(db):
    """A throwaway user, removed with everything hanging off it."""
    created: list[int] = []

    def make(role_key: str = VIEWER, is_external: bool = False) -> UserDB:
        email = f"test-{uuid.uuid4().hex[:12]}@example.invalid"
        user = auth.create_user(db, email=email, role_key=role_key, is_external=is_external)
        created.append(user.id)
        return user

    yield make

    for user_id in created:
        db.query(SessionDB).filter(SessionDB.user_id == user_id).delete()
        db.query(LoginCodeDB).filter(LoginCodeDB.user_id == user_id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user_id).delete()
        db.query(UserDB).filter(UserDB.id == user_id).delete()
    db.commit()


class TestSeeding:

    def test_default_brand_always_exists(self, db):
        # ADR-150 §4: one implicit brand, so the scope column is never dangling.
        assert auth.ensure_default_brand(db).key == auth.DEFAULT_BRAND_KEY

    def test_three_roles_are_seeded(self, db):
        keys = {r.key for r in db.query(RoleDB).all()}
        assert {ADMIN, MANAGER, VIEWER} <= keys

    def test_builtin_roles_are_protected_from_deletion(self, db):
        for key in (ADMIN, MANAGER, VIEWER):
            assert db.query(RoleDB).filter(RoleDB.key == key).first().is_builtin is True

    def test_seeding_twice_is_idempotent(self, db):
        before = db.query(RoleDB).count()
        auth.ensure_builtin_roles(db)
        assert db.query(RoleDB).count() == before


class TestPermissions:

    def test_admin_can_manage_users_and_credentials(self, db, temp_user):
        user = temp_user(role_key=ADMIN)
        assert auth.has_permission(db, user, USERS_MANAGE)
        assert auth.has_permission(db, user, CREDENTIALS_MANAGE)

    def test_manager_can_run_ai_but_not_touch_credentials(self, db, temp_user):
        # The line ADR-152's write-only credential rule leans on.
        user = temp_user(role_key=MANAGER)
        assert auth.has_permission(db, user, AI_RUN)
        assert not auth.has_permission(db, user, CREDENTIALS_MANAGE)
        assert not auth.has_permission(db, user, USERS_MANAGE)

    def test_viewer_can_only_view(self, db, temp_user):
        user = temp_user(role_key=VIEWER)
        assert auth.permissions_for(db, user) == {VIEW}

    def test_deactivated_user_holds_nothing(self, db, temp_user):
        user = temp_user(role_key=ADMIN)
        auth.set_active(db, user.id, False)
        assert auth.permissions_for(db, user) == set()

    def test_permissions_can_be_narrowed_to_one_brand(self, db, temp_user):
        user = temp_user(role_key=ADMIN)
        brand = auth.ensure_default_brand(db)
        assert auth.has_permission(db, user, USERS_MANAGE, brand_id=brand.id)
        # A brand the user holds no grant on yields nothing.
        assert auth.permissions_for(db, user, brand_id=brand.id + 9999) == set()


class TestMultiBrandGrants:

    def test_a_user_can_hold_different_roles_on_different_brands(self, db, temp_user):
        # The reason grants are rows rather than a multi-value column: an array
        # of brand ids on one role row cannot express Admin here, Viewer there.
        user = temp_user(role_key=VIEWER)
        second = auth.BrandDB(key=f"b-{uuid.uuid4().hex[:8]}", name="Second")
        db.add(second)
        db.commit()
        db.refresh(second)
        admin_role = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
        db.add(RoleAssignmentDB(user_id=user.id, role_id=admin_role.id, brand_id=second.id))
        db.commit()

        default = auth.ensure_default_brand(db)
        assert auth.permissions_for(db, user, brand_id=default.id) == {VIEW}
        assert USERS_MANAGE in auth.permissions_for(db, user, brand_id=second.id)

        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.brand_id == second.id).delete()
        db.query(auth.BrandDB).filter(auth.BrandDB.id == second.id).delete()
        db.commit()


class TestSignIn:

    def test_code_signs_a_user_in(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        code = auth.request_login_code(db, user.email)
        assert code and len(code) == 6

        token = auth.verify_login_code(db, user.email, code)
        assert token
        assert auth.user_for_token(db, token).id == user.id

    def test_email_is_normalised(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        code = auth.request_login_code(db, user.email.upper())
        assert auth.verify_login_code(db, f"  {user.email.upper()}  ", code)

    def test_unknown_address_yields_no_code(self, db, monkeypatch):
        # Enumeration resistance: the caller cannot tell a real address from a
        # fake one, because neither produces anything distinguishable.
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        assert auth.request_login_code(db, "nobody@example.invalid") is None

    def test_deactivated_user_cannot_request_a_code(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        auth.set_active(db, user.id, False)
        assert auth.request_login_code(db, user.email) is None

    def test_code_is_single_use(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        code = auth.request_login_code(db, user.email)
        assert auth.verify_login_code(db, user.email, code)
        assert auth.verify_login_code(db, user.email, code) is None

    def test_wrong_code_is_rejected(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        auth.request_login_code(db, user.email)
        assert auth.verify_login_code(db, user.email, "000000") is None

    def test_code_burns_after_too_many_attempts(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        code = auth.request_login_code(db, user.email)
        for _ in range(auth.CODE_MAX_ATTEMPTS):
            auth.verify_login_code(db, user.email, "000000")
        # Even the correct code no longer works — better than leaving a
        # guessable one alive for the rest of its TTL.
        assert auth.verify_login_code(db, user.email, code) is None

    def test_expired_code_is_rejected(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        code = auth.request_login_code(db, user.email)
        row = db.query(LoginCodeDB).filter(LoginCodeDB.user_id == user.id).first()
        row.expires_at = auth.now() - timedelta(seconds=1)
        db.commit()
        assert auth.verify_login_code(db, user.email, code) is None

    def test_requesting_again_supersedes_the_previous_code(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        first = auth.request_login_code(db, user.email)
        second = auth.request_login_code(db, user.email)
        assert auth.verify_login_code(db, user.email, first) is None
        assert auth.verify_login_code(db, user.email, second)

    def test_plaintext_code_is_never_stored(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        code = auth.request_login_code(db, user.email)
        row = db.query(LoginCodeDB).filter(LoginCodeDB.user_id == user.id).first()
        assert row.code_hash != code
        assert row.code_hash == auth.hash_secret(code)


class TestSessions:

    def test_revoking_ends_the_session(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        token = auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        auth.revoke_token(db, token)
        assert auth.user_for_token(db, token) is None

    def test_deactivating_a_user_kills_live_sessions_immediately(self, db, temp_user, monkeypatch):
        # ADR-151 §5: deactivation is the whole offboarding control, so it has
        # to bite now rather than at next expiry.
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        token = auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        assert auth.user_for_token(db, token) is not None

        auth.set_active(db, user.id, False)
        assert auth.user_for_token(db, token) is None

    def test_idle_timeout_ends_the_session(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        token = auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        row = db.query(SessionDB).filter(SessionDB.user_id == user.id).first()
        row.last_seen_at = auth.now() - timedelta(minutes=auth.SESSION_IDLE_MINUTES + 1)
        db.commit()
        assert auth.user_for_token(db, token) is None

    def test_absolute_expiry_ends_the_session(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        token = auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        row = db.query(SessionDB).filter(SessionDB.user_id == user.id).first()
        row.expires_at = auth.now() - timedelta(seconds=1)
        db.commit()
        assert auth.user_for_token(db, token) is None

    def test_garbage_token_resolves_to_nobody(self, db):
        assert auth.user_for_token(db, "not-a-real-token") is None
        assert auth.user_for_token(db, None) is None

    def test_plaintext_token_is_never_stored(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        token = auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        row = db.query(SessionDB).filter(SessionDB.user_id == user.id).first()
        assert row.token_hash != token


class TestUserAdministration:

    def test_duplicate_email_is_refused(self, db, temp_user):
        user = temp_user()
        assert auth.create_user(db, email=user.email) is None

    def test_external_flag_shows_in_the_access_list(self, db, temp_user):
        user = temp_user(is_external=True)
        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)
        assert row["user"].is_external is True
        assert row["grants"]

    def test_access_list_counts_live_sessions(self, db, temp_user, monkeypatch):
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user()
        auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)
        assert row["live_sessions"] == 1


@pytest.fixture
def temp_role(db):
    """A throwaway role, removed even when the test fails.

    Previously each test cleaned up its own role on the last line, so a failing
    assertion leaked one into the shared database — which duly happened.
    """
    created: list[int] = []

    def make(name: str = "Editor", copy_from_role_id: int | None = None):
        role = auth.create_role(
            db, key=f"tmp-{uuid.uuid4().hex[:8]}", name=name,
            copy_from_role_id=copy_from_role_id,
        )
        created.append(role.id)
        return role

    yield make

    for role_id in created:
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.role_id == role_id).delete()
        db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role_id).delete()
        db.query(RoleDB).filter(RoleDB.id == role_id).delete()
    db.commit()


class TestRoleAdministration:
    """The gap this closes: a role used to be fixed at creation."""

    def test_a_role_can_be_added_after_creation(self, db, temp_user):
        user = temp_user(role_key=VIEWER)
        admin_role = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
        assert auth.assign_role(db, user.id, admin_role.id) is True
        assert USERS_MANAGE in auth.permissions_for(db, user)

    def test_assigning_twice_is_idempotent(self, db, temp_user):
        user = temp_user(role_key=VIEWER)
        role = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
        assert auth.assign_role(db, user.id, role.id) is True
        assert auth.assign_role(db, user.id, role.id) is False

    def test_two_roles_resolve_in_the_users_favour(self, db, temp_user):
        # Union, not intersection — and it falls out of the model rather than
        # being a rule, because permissions are grants only with no DENY.
        user = temp_user(role_key=VIEWER)
        manager = db.query(RoleDB).filter(RoleDB.key == MANAGER).first()
        auth.assign_role(db, user.id, manager.id)
        held = auth.permissions_for(db, user)
        assert VIEW in held and AI_RUN in held

    def test_revoking_one_grant_leaves_the_others(self, db, temp_user):
        user = temp_user(role_key=VIEWER)
        manager = db.query(RoleDB).filter(RoleDB.key == MANAGER).first()
        auth.assign_role(db, user.id, manager.id)
        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)
        manager_grant = next(g for g in row["grants"] if g["role"] == "Manager")

        assert auth.revoke_assignment(db, manager_grant["id"]) is True
        assert auth.permissions_for(db, user) == {VIEW}

    def test_revoking_a_role_does_not_end_the_session(self, db, temp_user, monkeypatch):
        # Losing scope is not being thrown out mid-edit; the next request is
        # checked against the new permissions anyway. Deactivation is the
        # control that ends a session.
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        user = temp_user(role_key=VIEWER)
        token = auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)
        auth.revoke_assignment(db, row["grants"][0]["id"])
        assert auth.user_for_token(db, token) is not None


class TestRoleEditing:

    def _held(self, db, role):
        return next(
            r["permissions"] for r in auth.roles_with_permissions(db)
            if r["role"].id == role.id
        )

    def test_a_role_can_be_created_from_a_preset(self, db, temp_role):
        manager = db.query(RoleDB).filter(RoleDB.key == MANAGER).first()
        role = temp_role(copy_from_role_id=manager.id)
        assert AI_RUN in self._held(db, role)  # inherited from the preset it copied

    def test_duplicate_key_is_refused(self, db):
        assert auth.create_role(db, key=ADMIN, name="Nope") is None

    def test_permissions_can_be_changed_individually(self, db, temp_role):
        role = temp_role()
        auth.set_role_permissions(db, role.id, [CREDENTIALS_MANAGE])
        # VIEW is always implied, so it survives even when not requested.
        assert self._held(db, role) == {CREDENTIALS_MANAGE, VIEW}

    def test_unknown_permission_keys_are_dropped(self, db, temp_role):
        # A key naming no code path grants nothing; storing it would imply it did.
        role = temp_role()
        auth.set_role_permissions(db, role.id, ["not.a.real.permission"])
        assert self._held(db, role) == {VIEW}

    def test_editing_a_shipped_role_stops_the_preset_overwriting_it(self, db):
        # The trap this guards: without it, the next restart silently reverts a
        # deliberate change.
        viewer = db.query(RoleDB).filter(RoleDB.key == VIEWER).first()
        original = {r.permission for r in db.query(RolePermissionDB)
                    .filter(RolePermissionDB.role_id == viewer.id).all()}
        try:
            auth.set_role_permissions(db, viewer.id, [VIEW, AI_RUN])
            assert viewer.is_customised is True

            auth.ensure_builtin_roles(db)  # what startup does
            held = {r.permission for r in db.query(RolePermissionDB)
                    .filter(RolePermissionDB.role_id == viewer.id).all()}
            assert AI_RUN in held, "startup reverted a customised role"
        finally:
            db.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == viewer.id).delete()
            for p in original:
                db.add(RolePermissionDB(role_id=viewer.id, permission=p))
            viewer.is_customised = False
            db.commit()

    def test_shipped_roles_cannot_be_deleted(self, db):
        admin = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
        assert "cannot be deleted" in auth.delete_role(db, admin.id)

    def test_a_role_someone_holds_cannot_be_deleted(self, db, temp_user, temp_role):
        role = temp_role()
        user = temp_user(role_key=VIEWER)
        auth.assign_role(db, user.id, role.id)
        assert "still hold" in auth.delete_role(db, role.id)
        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)
        for g in row["grants"]:
            auth.revoke_assignment(db, g["id"])
        assert auth.delete_role(db, role.id) is None


class TestPostLoginRedirect:
    """Where a user lands after signing in.

    Two bugs found in real use: sign-in sent everyone to /ui/users, so a Viewer
    landed on a 403 with no navigation and was effectively locked out of a
    system they had just authenticated to.
    """

    def test_no_target_lands_on_the_dashboard(self):
        assert auth.safe_next(None) == "/"
        assert auth.safe_next("") == "/"
        assert auth.safe_next("   ") == "/"

    def test_a_same_site_path_is_kept(self):
        assert auth.safe_next("/ui/campaigns") == "/ui/campaigns"
        assert auth.safe_next("/ui/content?status=draft") == "/ui/content?status=draft"

    def test_an_absolute_url_is_refused(self):
        # Open redirect: a link to our own login page carrying an attacker's
        # host, so the victim signs in for real and lands somewhere hostile.
        assert auth.safe_next("https://evil.example/phish") == "/"
        assert auth.safe_next("http://evil.example") == "/"

    def test_a_protocol_relative_url_is_refused(self):
        # //host is a URL, not a path, and browsers treat it as one.
        assert auth.safe_next("//evil.example/phish") == "/"

    def test_backslashes_are_refused(self):
        # Some clients normalise \ to /, turning this into //evil.example.
        assert auth.safe_next("/\\evil.example") == "/"
        assert auth.safe_next("\\\\evil.example") == "/"

    def test_header_injection_attempts_are_refused(self):
        assert auth.safe_next("/ui/x\r\nSet-Cookie: a=b") == "/"


class TestSignInCodeIsNeverDisclosed:
    """Gate 4b (P0) and the enumeration oracle beside it (P1).

    These were filed as two bugs and are one change: `deliver_code` returned
    False both when the dev path skipped sending and when a real send failed,
    so `request_login_code` could not tell them apart and returned the live
    code in both cases. A deployment with a broken mail provider handed a
    working sign-in code to anyone who typed an admin's address — and the
    handler's 200-with-code vs 303-redirect branch told an unauthenticated
    visitor which addresses were real.

    ADR-151 §2 requires an identical response whether or not the address
    exists, with no dev carve-out. Decided 2026-09-13: that holds everywhere,
    including the demo configuration, and the dev code goes to the log.
    """

    def test_failed_real_send_does_not_return_the_code(self, db, temp_user, monkeypatch):
        """The P0 itself. A send that was attempted and failed returns nothing."""
        user = temp_user()
        # Force the real-provider path, then make the send fail.
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "resend")
        monkeypatch.delenv("AUTH_DEV_SHOW_CODE", raising=False)
        monkeypatch.setattr(
            auth, "deliver_code", lambda email, code: auth.CodeDelivery.failed
        )

        assert auth.request_login_code(db, user.email) is None, (
            "a sign-in code was returned after a real delivery attempt failed — "
            "this is the P0: a misconfigured mail provider hands a working code "
            "to whoever typed the address"
        )

    def test_successful_real_send_does_not_return_the_code(self, db, temp_user, monkeypatch):
        user = temp_user()
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "resend")
        monkeypatch.delenv("AUTH_DEV_SHOW_CODE", raising=False)
        monkeypatch.setattr(
            auth, "deliver_code", lambda email, code: auth.CodeDelivery.sent
        )

        assert auth.request_login_code(db, user.email) is None

    def test_dev_path_still_returns_the_code_for_local_use(self, db, temp_user, monkeypatch):
        """The one case that may return it — and it is already in the log.

        Without this the suite could pass by never returning a code at all,
        and every other test here signs in through this path.
        """
        user = temp_user()
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        code = auth.request_login_code(db, user.email)
        assert code is not None and len(code) == 6

    def test_login_response_is_identical_for_known_and_unknown_addresses(
        self, db, temp_user, monkeypatch
    ):
        """The P1. The oracle was the 200-vs-303 branch, so compare responses.

        Runs against the default mock provider — the configuration a prospect
        is shown, and the one where the oracle used to be live.
        """
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user = temp_user()
        client = TestClient(app, follow_redirects=False)

        known = client.post("/ui/login", data={"email": user.email, "next": ""})
        unknown = client.post(
            "/ui/login",
            data={"email": f"nobody-{uuid.uuid4().hex[:8]}@example.invalid", "next": ""},
        )

        assert known.status_code == unknown.status_code == 303, (
            "the login form answered a known address differently from an "
            "unknown one — that difference is the enumeration oracle"
        )
        # The redirect target carries the address back, which differs by
        # construction; everything else about the response must match.
        assert known.headers["location"].split("email=")[0] == (
            unknown.headers["location"].split("email=")[0]
        )
        assert known.content == unknown.content

    def test_the_code_never_appears_in_the_login_response(
        self, db, temp_user, monkeypatch
    ):
        """Belt and braces: even in dev, the body must not carry the code."""
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user = temp_user()
        client = TestClient(app, follow_redirects=True)

        response = client.post("/ui/login", data={"email": user.email, "next": ""})

        latest = (
            db.query(LoginCodeDB)
            .filter(LoginCodeDB.user_id == user.id)
            .order_by(LoginCodeDB.id.desc())
            .first()
        )
        assert latest is not None, "no code was issued, so this proves nothing"
        # Codes are stored hashed, so scan the body for any six-digit run
        # rather than for the code itself.
        import re

        assert not re.search(r"\b\d{6}\b", response.text), (
            "a six-digit code appeared in the login response body"
        )


class TestDevCodePath:

    def test_mock_is_the_default_provider(self, monkeypatch):
        # Regression guard. This was once inferred from whether RESEND_API_KEY
        # happened to be set, which made "send for real" the default on any
        # developer machine holding a key for send testing — and duly emailed a
        # live message to a throwaway address. Enabling real sign-in mail is an
        # explicit act now.
        monkeypatch.delenv("SYSTEM_MAIL_PROVIDER", raising=False)
        monkeypatch.delenv("AUTH_DEV_SHOW_CODE", raising=False)
        monkeypatch.setenv("RESEND_API_KEY", "re_test")
        assert auth.system_mail_provider() == "mock"
        assert auth.dev_code_visible() is True

    def test_opting_into_a_real_provider_disables_the_dev_path(self, monkeypatch):
        monkeypatch.delenv("AUTH_DEV_SHOW_CODE", raising=False)
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "resend")
        assert auth.dev_code_visible() is False

    def test_explicit_override_wins(self, monkeypatch):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "resend")
        monkeypatch.setenv("AUTH_DEV_SHOW_CODE", "1")
        assert auth.dev_code_visible() is True

    def test_mock_provider_never_reaches_the_network(self, monkeypatch):
        # dev_code_visible() short-circuits before any provider is constructed,
        # so a misconfigured deployment cannot accidentally send.
        monkeypatch.delenv("SYSTEM_MAIL_PROVIDER", raising=False)
        monkeypatch.delenv("AUTH_DEV_SHOW_CODE", raising=False)
        # Tri-state, not a boolean: "nothing was attempted" must be
        # distinguishable from "a real send failed", because only the first
        # may ever hand the code back to the caller.
        assert (
            auth.deliver_code("someone@example.invalid", "123456")
            is auth.CodeDelivery.dev_not_attempted
        )


class TestCsrfIsActuallyEnforced:
    """The guard, exercised over HTTP rather than in isolation.

    Written after a mutation check caught the gap: unit tests covering the
    token derivation and the hidden field both passed with the guard disabled
    entirely, because neither one sent a request through it. A CSRF test that
    never makes a forged request proves nothing.

    The two refusal cases need no cleanup by construction — a rejected request
    never reaches its handler, so nothing is created.
    """

    def _client_and_token(self, db, user):
        from fastapi.testclient import TestClient

        from main import app

        token = auth.verify_login_code(db, user.email, auth.request_login_code(db, user.email))
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.SESSION_COOKIE, token)
        return client, auth.csrf_token_for(token)

    def test_post_without_a_token_is_refused(self, db, temp_user):
        from app.campaigns.db_models import CampaignDB

        user = temp_user(role_key="admin")
        client, _ = self._client_and_token(db, user)
        before = db.query(CampaignDB).count()

        response = client.post("/ui/campaigns", data={"name": "csrf-test-no-token"})

        assert response.status_code == 403
        db.expire_all()
        assert db.query(CampaignDB).count() == before, (
            "a request refused for CSRF still reached its handler"
        )

    def test_post_with_a_wrong_token_is_refused(self, db, temp_user):
        from app.campaigns.db_models import CampaignDB

        user = temp_user(role_key="admin")
        client, _ = self._client_and_token(db, user)
        before = db.query(CampaignDB).count()

        response = client.post(
            "/ui/campaigns",
            data={"name": "csrf-test-wrong-token", "csrf_token": "not-the-right-token"},
        )

        assert response.status_code == 403
        db.expire_all()
        assert db.query(CampaignDB).count() == before

    def test_post_with_the_right_token_goes_through(self, db, temp_user):
        """Without this, a guard that refused everything would pass the suite."""
        from app.campaigns.db_models import (
            CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB,
        )

        user = temp_user(role_key="admin")
        client, csrf = self._client_and_token(db, user)
        name = f"csrf-test-accepted-{uuid.uuid4().hex[:8]}"
        try:
            response = client.post(
                "/ui/campaigns", data={"name": name, "csrf_token": csrf}
            )
            assert response.status_code == 303, (
                f"a correctly-tokened form was refused ({response.status_code})"
            )
            db.expire_all()
            assert db.query(CampaignDB).filter(CampaignDB.name == name).count() == 1
        finally:
            # The route creates a variant alongside the campaign, so the
            # children go first or the delete hits a foreign key.
            for campaign in db.query(CampaignDB).filter(CampaignDB.name == name).all():
                variant_ids = [
                    v.id for v in db.query(VariantDB).filter(
                        VariantDB.campaign_id == campaign.id
                    ).all()
                ]
                if variant_ids:
                    db.query(ModuleInstanceDB).filter(
                        ModuleInstanceDB.variant_id.in_(variant_ids)
                    ).delete(synchronize_session=False)
                    db.query(DecisionSlotDB).filter(
                        DecisionSlotDB.variant_id.in_(variant_ids)
                    ).delete(synchronize_session=False)
                    db.query(VariantDB).filter(
                        VariantDB.campaign_id == campaign.id
                    ).delete(synchronize_session=False)
                db.delete(campaign)
            db.commit()


def _unique_address() -> str:
    return f"throttle-{uuid.uuid4().hex[:12]}@example.invalid"


class TestLoginCodeRequestThrottle:
    """Launch gate 4's last piece — ADR-151 §2's "rate limited per address and
    per IP", which was the half of that sentence nobody had built.

    `CODE_MAX_ATTEMPTS` capped how often a code could be **guessed**. Nothing
    capped how often one could be **asked for**, so a single unauthenticated
    visitor could trigger unlimited mail to any address they cared to guess —
    at the sender reputation that the rest of the system depends on.
    """

    def test_requests_are_allowed_up_to_the_address_limit(self, db, throttle_ip):
        address = _unique_address()
        for attempt in range(auth.CODE_REQUESTS_PER_ADDRESS):
            assert auth.login_request_allowed(db, address, throttle_ip) is True, (
                f"request {attempt + 1} was refused, below the limit of "
                f"{auth.CODE_REQUESTS_PER_ADDRESS}"
            )
        assert auth.login_request_allowed(db, address, throttle_ip) is False, (
            "the address limit did not bite — requesting a code is uncapped"
        )

    def test_the_limit_is_per_address_not_global(self, db, throttle_ip):
        exhausted = _unique_address()
        for _ in range(auth.CODE_REQUESTS_PER_ADDRESS):
            auth.login_request_allowed(db, exhausted, throttle_ip)
        assert auth.login_request_allowed(db, exhausted, throttle_ip) is False
        assert auth.login_request_allowed(db, _unique_address(), throttle_ip) is True, (
            "one exhausted address blocked a different one — the limit is "
            "counting the wrong thing"
        )

    def test_the_client_limit_bites_across_different_addresses(self, db, throttle_ip):
        """The per-IP half. Every address is distinct, so only the IP can stop this."""
        for attempt in range(auth.CODE_REQUESTS_PER_CLIENT):
            assert auth.login_request_allowed(db, _unique_address(), throttle_ip) is True, (
                f"request {attempt + 1} was refused below the client limit"
            )
        assert auth.login_request_allowed(db, _unique_address(), throttle_ip) is False, (
            "a single client walked through the per-IP limit by varying the "
            "address — which is exactly how an enumeration sweep is shaped"
        )

    def test_a_different_client_is_unaffected(self, db, throttle_ip):
        for _ in range(auth.CODE_REQUESTS_PER_CLIENT):
            auth.login_request_allowed(db, _unique_address(), throttle_ip)
        assert auth.login_request_allowed(db, _unique_address(), throttle_ip) is False

        other = f"203.0.113.{uuid.uuid4().hex[:8]}"
        try:
            assert auth.login_request_allowed(db, _unique_address(), other) is True, (
                "one exhausted client locked out everybody else"
            )
        finally:
            db.query(LoginCodeRequestDB).filter(
                LoginCodeRequestDB.client_hash == auth.hash_secret(other)
            ).delete(synchronize_session=False)
            db.commit()

    def test_a_refused_request_is_not_recorded(self, db, throttle_ip):
        """The anti-lockout property, and it is deliberate rather than incidental.

        If refusals counted, an attacker could hold a real person's address
        over the limit for as long as they kept hammering it — turning a
        mail-volume control into an indefinite denial of sign-in against any
        address they know. Counting only what was allowed bounds that to a
        single window.
        """
        address = _unique_address()
        for _ in range(auth.CODE_REQUESTS_PER_ADDRESS + 5):
            auth.login_request_allowed(db, address, throttle_ip)

        recorded = db.query(LoginCodeRequestDB).filter(
            LoginCodeRequestDB.address_hash == auth.hash_secret(address)
        ).count()
        assert recorded == auth.CODE_REQUESTS_PER_ADDRESS, (
            f"{recorded} rows recorded for {auth.CODE_REQUESTS_PER_ADDRESS} "
            "allowed requests — refusals are being counted, so an attacker can "
            "keep a victim locked out indefinitely"
        )

    def test_a_request_outside_the_window_stops_counting(self, db, throttle_ip):
        address = _unique_address()
        for _ in range(auth.CODE_REQUESTS_PER_ADDRESS):
            auth.login_request_allowed(db, address, throttle_ip)
        assert auth.login_request_allowed(db, address, throttle_ip) is False

        # Age every one of them past the window. The limit is a window, not a
        # lifetime cap — without this a real person who used their five is
        # locked out of the product permanently.
        db.query(LoginCodeRequestDB).filter(
            LoginCodeRequestDB.address_hash == auth.hash_secret(address)
        ).update(
            {"created_at": auth.now() - timedelta(
                minutes=auth.CODE_REQUEST_ADDRESS_WINDOW_MINUTES + 1)},
            synchronize_session=False,
        )
        db.commit()

        assert auth.login_request_allowed(db, address, throttle_ip) is True, (
            "the window never reopens — the limit is a permanent lockout"
        )

    def test_the_address_is_normalised_before_counting(self, db, throttle_ip):
        """Otherwise changing the case of one letter buys a fresh allowance."""
        address = _unique_address()
        for _ in range(auth.CODE_REQUESTS_PER_ADDRESS):
            auth.login_request_allowed(db, address, throttle_ip)

        assert auth.login_request_allowed(db, f"  {address.upper()}  ", throttle_ip) is False, (
            "ANNA@x.com and anna@x.com counted as two addresses, so the limit "
            "is bypassed by shouting"
        )

    def test_neither_identifier_is_stored_raw(self, db, throttle_ip):
        """ADR-154: accountability records carry ids, not contact details.

        A throttle necessarily counts attempts for addresses that may belong to
        nobody, so the table would otherwise become a list of who *tried* to
        sign in — assembled from unauthenticated input.
        """
        address = _unique_address()
        auth.login_request_allowed(db, address, throttle_ip)

        row = (
            db.query(LoginCodeRequestDB)
            .filter(LoginCodeRequestDB.address_hash == auth.hash_secret(address))
            .first()
        )
        assert row is not None
        assert row.address_hash == auth.hash_secret(auth.normalise_email(address))
        assert row.client_hash == auth.hash_secret(throttle_ip)

        stored = f"{row.address_hash}{row.client_hash}"
        assert address.split("@")[0] not in stored
        assert throttle_ip not in stored

    def test_rows_outside_every_window_are_pruned_on_write(self, db, throttle_ip):
        stale = LoginCodeRequestDB(
            address_hash=auth.hash_secret(_unique_address()),
            client_hash=auth.hash_secret(throttle_ip),
            created_at=auth.now() - timedelta(
                minutes=max(auth.CODE_REQUEST_ADDRESS_WINDOW_MINUTES,
                            auth.CODE_REQUEST_CLIENT_WINDOW_MINUTES) + 5),
        )
        db.add(stale)
        db.commit()
        stale_id = stale.id

        auth.login_request_allowed(db, _unique_address(), throttle_ip)

        assert db.query(LoginCodeRequestDB).filter(
            LoginCodeRequestDB.id == stale_id
        ).first() is None, (
            "a row that can never affect a decision again was kept — the table "
            "grows forever, accumulating hashes of everyone who tried to sign in"
        )


class TestTheLoginRouteIsActuallyThrottled:
    """The connecting line, over HTTP.

    Written this way on purpose. Twice in one day the unit tests either side of
    a defect both passed while the line joining them was never exercised — the
    CSRF guard could be switched off entirely without failing anything. So the
    question here is not "does `login_request_allowed` count correctly" but
    "does the route stop issuing codes", which is the behaviour the gate is
    about.
    """

    def test_no_further_code_is_issued_once_the_limit_is_reached(
        self, db, temp_user, monkeypatch
    ):
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user = temp_user()
        client = TestClient(app, follow_redirects=False)

        def codes_issued() -> int:
            return db.query(LoginCodeDB).filter(LoginCodeDB.user_id == user.id).count()

        for _ in range(auth.CODE_REQUESTS_PER_ADDRESS):
            client.post("/ui/login", data={"email": user.email, "next": ""})
        at_limit = codes_issued()
        assert at_limit == auth.CODE_REQUESTS_PER_ADDRESS, (
            f"{at_limit} codes issued for {auth.CODE_REQUESTS_PER_ADDRESS} "
            "requests — this test cannot prove anything about the one after"
        )

        client.post("/ui/login", data={"email": user.email, "next": ""})

        assert codes_issued() == at_limit, (
            "the route issued a code past the limit — the throttle exists but "
            "the request path does not go through it"
        )

    def test_a_throttled_response_is_indistinguishable(
        self, db, temp_user, monkeypatch
    ):
        """A distinct 429 would say "your probe was counted", per address.

        That is the enumeration oracle re-opened through the back door: the
        response would differ for an address someone else is also probing.
        """
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user = temp_user()
        client = TestClient(app, follow_redirects=False)

        allowed = client.post("/ui/login", data={"email": user.email, "next": ""})
        for _ in range(auth.CODE_REQUESTS_PER_ADDRESS):
            client.post("/ui/login", data={"email": user.email, "next": ""})
        throttled = client.post("/ui/login", data={"email": user.email, "next": ""})

        assert allowed.status_code == throttled.status_code == 303
        assert allowed.headers["location"] == throttled.headers["location"]
        assert allowed.content == throttled.content


class TestWhichAddressTheLimitCounts:
    """`X-Forwarded-For` is attacker-controlled unless a proxy overwrites it."""

    def test_the_header_is_ignored_by_default(self, monkeypatch):
        monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
        assert auth.client_identifier("10.0.0.1", "1.2.3.4") == "10.0.0.1", (
            "an unauthenticated caller set a header and got a fresh rate-limit "
            "identity, so the per-IP limit does not exist"
        )

    def test_the_header_is_used_when_explicitly_trusted(self, monkeypatch):
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
        assert auth.client_identifier("10.0.0.1", "1.2.3.4") == "1.2.3.4"

    def test_only_the_left_most_entry_is_taken(self, monkeypatch):
        # The rest of the chain is the proxies it passed through.
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
        assert auth.client_identifier("10.0.0.1", "1.2.3.4, 10.0.0.9") == "1.2.3.4"

    def test_a_trusted_deployment_still_falls_back_without_the_header(self, monkeypatch):
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
        assert auth.client_identifier("10.0.0.1", None) == "10.0.0.1"

    def test_a_missing_peer_is_not_an_error(self, monkeypatch):
        # ASGI allows request.client to be None. Everything with no peer then
        # shares one bucket, which is restrictive rather than open.
        monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
        assert auth.client_identifier(None, None) == ""


class TestSubAddressedAddressesCanSignIn:
    """P1 — any address containing `+` could never sign in through the UI.

    `/ui/login` interpolated the address into the redirect's query string
    unescaped while the `next` parameter beside it on the same line *was*
    escaped. Starlette decodes `+` in a query value as a space, so
    `name+tag@example.com` reached the verify form as `name tag@example.com`,
    was written into the form's hidden field, posted back mangled, and
    `verify_login_code` found no user — reporting *"that code is not valid or
    has expired"*. The wrong diagnosis, which is what made it expensive.

    Invisible in development: `dev_code_visible()` is true under the shipped
    `mock` default, and the old handler rendered the verify page inline instead
    of taking this redirect. The bug existed only in deployments with a real
    provider — the ones that matter. Sub-addressing is common in this product's
    operator population.
    """

    @pytest.fixture
    def plus_user(self, db):
        email = f"ops+tag-{uuid.uuid4().hex[:8]}@example.invalid"
        user = auth.create_user(db, email=email, role_key=VIEWER)
        yield user
        db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
        db.query(LoginCodeDB).filter(LoginCodeDB.user_id == user.id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
        db.query(UserDB).filter(UserDB.id == user.id).delete()
        db.commit()

    def test_the_address_the_verify_form_posts_back_is_the_real_one(
        self, db, plus_user, monkeypatch
    ):
        """The whole defect, at the only layer that shows it.

        Asserting on the redirect's Location would not do: the bug is in what
        the *next* request receives after Starlette decodes it, and the hidden
        field is what the browser actually sends back.
        """
        import re

        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client = TestClient(app, follow_redirects=True)

        page = client.post("/ui/login", data={"email": plus_user.email, "next": ""})

        field = re.search(r'name="email"\s+value="([^"]*)"', page.text)
        assert field is not None, "the verify form has no email field to post back"
        assert field.group(1) == plus_user.email, (
            f"the form will post back {field.group(1)!r} instead of "
            f"{plus_user.email!r} — the user is told their code is invalid"
        )

    def test_a_mangled_address_really_does_fail_to_sign_in(self, db, plus_user):
        """Why the above matters, rather than being a cosmetic difference."""
        code = auth.request_login_code(db, plus_user.email)
        assert code is not None

        mangled = plus_user.email.replace("+", " ")
        assert auth.verify_login_code(db, mangled, code) is None
        # ...and the untouched address still works, so this proves the space is
        # the cause rather than the code being spent.
        assert auth.verify_login_code(db, plus_user.email, code) is not None

    def test_the_retry_redirect_escapes_it_too(self, db, plus_user, monkeypatch):
        """The second interpolation — a wrong code sends you round again.

        Fixing only the first would leave the address intact until the user's
        first typo, then mangle it for every attempt after.
        """
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client = TestClient(app, follow_redirects=False)

        response = client.post(
            "/ui/login/verify",
            data={"email": plus_user.email, "code": "000000", "next": ""},
        )

        assert response.status_code == 303
        assert "%2B" in response.headers["location"], (
            "the retry redirect passed `+` through raw, so the address is "
            "mangled from the second attempt onwards"
        )


class TestSessionCookieIsSecure:
    """B9(c) — the session cookie set `HttpOnly` and `SameSite=Lax` but not
    `Secure`, so a reachable HTTP path transmitted the session token in clear.

    The other two flags do not cover this between them: `HttpOnly` stops script
    reading the cookie and `SameSite` blunts cross-site POST, but neither says
    anything to a network observer. A reference implementation people are meant
    to copy should not ship the gap.
    """

    def _sign_in(self, db, user, monkeypatch):
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client = TestClient(app, follow_redirects=False)
        code = auth.request_login_code(db, user.email)
        return client.post(
            "/ui/login/verify",
            data={"email": user.email, "code": code, "next": ""},
        )

    def test_the_cookie_carries_secure_by_default(self, db, temp_user, monkeypatch):
        monkeypatch.delenv("AUTH_COOKIE_INSECURE", raising=False)
        response = self._sign_in(db, temp_user(), monkeypatch)

        header = response.headers["set-cookie"]
        assert auth.SESSION_COOKIE in header, "no session cookie was set at all"
        assert "Secure" in header, (
            f"the session cookie shipped without Secure: {header!r} — a plain-HTTP "
            "request would transmit the session token in clear"
        )
        # The other two are not a substitute, but they must not have been lost
        # while adding the third.
        # Starlette emits `SameSite=lax` lowercase, so compare case-insensitively
        # rather than pinning a spelling the framework is free to change.
        lowered = header.lower()
        assert "httponly" in lowered and "samesite=lax" in lowered

    def test_the_escape_hatch_removes_it(self, db, temp_user, monkeypatch):
        """It has to actually work, or a Safari developer is locked out.

        Chrome and Firefox send a Secure cookie to http://localhost anyway;
        Safari historically does not, and the failure there is a login form
        that silently loops with nothing to read.
        """
        monkeypatch.setenv("AUTH_COOKIE_INSECURE", "true")
        response = self._sign_in(db, temp_user(), monkeypatch)

        header = response.headers["set-cookie"]
        assert auth.SESSION_COOKIE in header
        assert "Secure" not in header, (
            "AUTH_COOKIE_INSECURE did not take effect, so the documented way out "
            "of a localhost lockout does not work"
        )

    def test_the_default_is_secure_not_merely_unset(self, monkeypatch):
        # Guards the direction of the check: reading the env var with the wrong
        # polarity would make every deployment insecure and no other test here
        # would notice, because both cases above set the variable explicitly.
        monkeypatch.delenv("AUTH_COOKIE_INSECURE", raising=False)
        assert auth.cookie_secure() is True
        monkeypatch.setenv("AUTH_COOKIE_INSECURE", "")
        assert auth.cookie_secure() is True
