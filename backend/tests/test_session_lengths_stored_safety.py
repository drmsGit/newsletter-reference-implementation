"""Stored session lengths must preserve ADR-151's safe limits."""
from datetime import timedelta

import pytest

from app.auth import service as auth
from app.settings import service as settings
from tests.test_session_lengths import _session
from tests.test_session_lengths import db, restore_lengths, user  # noqa: F401


@pytest.mark.parametrize("hours,minutes,expected", [
    (1000, 1000, (72, 480)),
    (0, 0, (1, 5)),
    ("broken", "broken", (12, 60)),
    (1, 480, (1, 60)),
])
def test_unsafe_stored_lengths_cannot_extend_a_session_past_the_safe_lifetime(
    db, user, monkeypatch, hours, minutes, expected,  # noqa: F811
):
    settings.set_config(db, settings.SESSION_ABSOLUTE_HOURS_KEY, hours)
    settings.set_config(db, settings.SESSION_IDLE_MINUTES_KEY, minutes)
    assert settings.get_session_lengths(db) == expected
    token, row = _session(db, user)
    # Keep activity fresh: this tests the absolute limit, not idle expiry.
    boundary = row.created_at + timedelta(hours=expected[0])
    row.last_seen_at = boundary - timedelta(seconds=1)
    db.commit()
    monkeypatch.setattr(auth, "now", lambda: boundary - timedelta(seconds=1))
    assert auth._session_user(db, token, touch=False) is not None
    monkeypatch.setattr(auth, "now", lambda: boundary)
    assert auth._session_user(db, token, touch=False) is None
