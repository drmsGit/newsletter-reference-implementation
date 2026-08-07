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
    LoginCodeDB, RoleAssignmentDB, RoleDB, SessionDB, UserDB,
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
        assert auth.deliver_code("someone@example.invalid", "123456") is False
