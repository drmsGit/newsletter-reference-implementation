"""Session lengths are company settings within safe ranges (task-342; ADR-151
and its 2026-10-09 and 2026-10-11 addenda).

The absolute lifetime is 1 to 72 hours, the idle timeout 5 to 480 minutes
and never longer than the lifetime. A shorter length applies at once to
everyone signed in; a longer lifetime only to sessions started afterwards; a
longer idle timeout at once. The attack-resistance numbers stay in code.
"""
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.db_models import SessionDB
from app.auth.permissions import SETTINGS_MANAGE, VIEW
from app.database import SessionLocal
from app.settings import service as settings
from app.settings.db_models import AppConfigDB
from main import app
from tests.machine import machine
from tests.test_api_guard import signed_in

client = TestClient(app, raise_server_exceptions=False)
KEYS = (settings.SESSION_ABSOLUTE_HOURS_KEY, settings.SESSION_IDLE_MINUTES_KEY)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def restore_lengths(db):
    yield
    db.rollback()
    db.query(AppConfigDB).filter(AppConfigDB.key.in_(KEYS)).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def user(db):
    created = auth.create_user(db, email=f"len-{uuid.uuid4().hex[:8]}@example.invalid", role_key="manager")
    yield created
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": created.id})
    db.execute(text("DELETE FROM audit_events WHERE actor_id = :u"), {"u": created.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": created.id})
    db.commit()


def _session(db, user, *, started_hours_ago=0.0, idle_minutes=0.0):
    token = auth.create_session(db, user)
    row = db.query(SessionDB).filter(SessionDB.token_hash == auth.hash_secret(token)).one()
    row.created_at = row.created_at - timedelta(hours=started_hours_ago)
    row.expires_at = row.expires_at - timedelta(hours=started_hours_ago)
    row.last_seen_at = auth.now() - timedelta(minutes=idle_minutes)
    db.commit()
    return token, row


# --- the ranges ----------------------------------------------------------------

def test_the_defaults_are_twelve_hours_and_an_hour(db):
    assert settings.get_session_lengths(db) == (12, 60)


@pytest.mark.parametrize("hours, minutes", [(0, 60), (73, 60), (12, 4), (12, 481), (1, 61)])
def test_lengths_outside_the_safe_ranges_are_refused(db, hours, minutes):
    with pytest.raises(settings.SettingsInvalid):
        settings.save_session_lengths(db, hours, minutes)
    assert settings.get_session_lengths(db) == (12, 60)


def test_lengths_inside_are_kept(db):
    settings.save_session_lengths(db, 72, 480)
    assert settings.get_session_lengths(db) == (72, 480)
    settings.save_session_lengths(db, 1, 5)
    assert settings.get_session_lengths(db) == (1, 5)


# --- existing sessions -------------------------------------------------------------

def test_a_shorter_lifetime_ends_an_existing_session_at_once(db, user):
    token, _ = _session(db, user, started_hours_ago=3)
    assert auth.user_for_token(db, token) is not None
    settings.save_session_lengths(db, 2, 60)
    assert auth.user_for_token(db, token) is None


def test_a_longer_lifetime_does_not_extend_an_existing_session(db, user):
    token, _ = _session(db, user, started_hours_ago=13)   # past its 12 hours
    settings.save_session_lengths(db, 24, 60)
    assert auth.user_for_token(db, token) is None, "an old session was silently extended"


def test_a_longer_lifetime_reaches_new_sessions(db, user):
    settings.save_session_lengths(db, 24, 60)
    _, row = _session(db, user)
    assert row.expires_at - row.created_at > timedelta(hours=23)


def test_a_shorter_idle_timeout_applies_at_once(db, user):
    token, _ = _session(db, user, idle_minutes=30)
    assert auth._session_user(db, token, touch=False) is not None
    settings.save_session_lengths(db, 12, 20)
    assert auth._session_user(db, token, touch=False) is None


def test_a_longer_idle_timeout_applies_at_once(db, user):
    token, _ = _session(db, user, idle_minutes=90)
    assert auth._session_user(db, token, touch=False) is None
    settings.save_session_lengths(db, 12, 120)
    assert auth._session_user(db, token, touch=False) is not None


def test_the_attack_numbers_stay_in_code():
    """ADR-151's 2026-10-09 addendum: not settings, a stated exception."""
    for name in ("CODE_TTL_MINUTES", "CODE_REQUESTS_PER_ADDRESS", "CODE_REQUESTS_PER_CLIENT"):
        assert isinstance(getattr(auth, name), int), name
    assert not any("code" in key for key in KEYS)


# --- through the API ----------------------------------------------------------------

def test_a_person_with_settings_manage_sets_them_and_it_is_audited(db):
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.put("/settings/session-lengths", json={"absolute_hours": 8, "idle_minutes": 30},
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert response.json() == {"absolute_hours": 8, "idle_minutes": 30}
        shown = cookied.get("/settings").json()
        assert (shown["session_absolute_hours"], shown["session_idle_minutes"]) == (8, 30)
    entry = (db.query(AuditEventDB).filter(AuditEventDB.action == "settings.changed")
             .order_by(AuditEventDB.id.desc()).first())
    assert entry.detail["setting"] == "session_lengths"


def test_out_of_range_through_the_api_is_a_422(db):
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.put("/settings/session-lengths", json={"absolute_hours": 100, "idle_minutes": 30},
                               headers={"X-CSRF-Token": csrf})
    assert response.status_code == 422


def test_a_machine_cannot_change_them(db):
    with machine([VIEW, SETTINGS_MANAGE]) as headers:
        response = client.put("/settings/session-lengths", json={"absolute_hours": 8, "idle_minutes": 30},
                              headers=headers)
    assert response.status_code == 403


def test_the_cookie_lasts_as_long_as_the_setting_at_sign_in(db, user):
    settings.save_session_lengths(db, 8, 30)
    # Minted directly rather than requested through the API: the request route
    # is rate limited per client, and the suite's earlier sign-ins use it up.
    from tests.test_json_session import _latest_code

    auth.issue_login_code(db, user.email)
    row = _latest_code(db, user.id)
    row.code_hash = auth.hash_login_code("424242")
    db.commit()
    response = client.post("/auth/session/verify", json={"email": user.email, "code": "424242"})
    assert response.status_code == 200, response.text
    assert f"Max-Age={8 * 3600}" in response.headers["set-cookie"]
