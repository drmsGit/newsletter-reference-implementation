"""Sign-in codes: single use and the guess budget hold under concurrency, and
issuing does the same expensive work for every address (task-316, task-317).

Both found by the external review of 2026-10-09.

task-316: `verify_login_code` read the unconsumed code without a row lock and
incremented `attempts` in Python, so two simultaneous correct submissions both
opened a session, and parallel wrong guesses overwrote each other's count.
ADR-151 section 2 requires single use and a bounded number of guesses.

task-317: `issue_login_code` returned at once for an unknown address but ran
the scrypt hash (task-35) for a known one before answering, so the response
time told a caller which addresses have accounts. Verification already does
the same KDF work on every path; issuing now does too.
"""
import threading
import uuid

import pytest
from sqlalchemy import text

from app.auth import service as auth
from app.auth.db_models import LoginCodeDB
from app.database import SessionLocal


@pytest.fixture
def user():
    db = SessionLocal()
    made = auth.create_user(db, email=f"race-{uuid.uuid4().hex[:8]}@example.invalid", role_key="viewer")
    try:
        yield made.email, made.id
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": made.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": made.id})
        db.commit()
        db.close()


def _issue(email: str) -> str:
    db = SessionLocal()
    try:
        return auth.issue_login_code(db, email).code
    finally:
        db.close()


def _together(n: int, attempt, monkeypatch) -> list:
    """Run `attempt` in n threads, each with its own session, lined up at the
    KDF so that without a lock they all read the code before any commits. With
    the lock only one reaches the KDF at a time; the barrier then times out
    and each goes on in turn."""
    barrier = threading.Barrier(n)
    real = auth.login_code_matches

    def lined_up(stored, code):
        try:
            barrier.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        return real(stored, code)

    monkeypatch.setattr(auth, "login_code_matches", lined_up)
    results: list = [None] * n

    def run(i):
        db = SessionLocal()
        try:
            results[i] = attempt(db)
        finally:
            db.close()

    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results


def test_one_code_opens_at_most_one_session(user, monkeypatch):
    email, _ = user
    code = _issue(email)
    tokens = _together(2, lambda db: auth.verify_login_code(db, email, code), monkeypatch)
    assert sum(1 for t in tokens if t) == 1, "one code opened two sessions"


def test_parallel_wrong_guesses_all_count(user, monkeypatch):
    email, user_id = user
    code = _issue(email)
    wrong = "000000" if code != "000000" else "111111"
    _together(auth.CODE_MAX_ATTEMPTS, lambda db: auth.verify_login_code(db, email, wrong), monkeypatch)
    db = SessionLocal()
    try:
        row = db.query(LoginCodeDB).filter_by(user_id=user_id).order_by(LoginCodeDB.id.desc()).first()
        assert row.attempts == auth.CODE_MAX_ATTEMPTS, f"{auth.CODE_MAX_ATTEMPTS} guesses counted as {row.attempts}"
    finally:
        db.close()
    # The budget is spent: the right code no longer opens a session.
    db = SessionLocal()
    try:
        assert auth.verify_login_code(db, email, code) is None
    finally:
        db.close()


def test_issuing_runs_the_same_kdf_work_for_every_address(user, monkeypatch):
    email, _ = user
    calls: list[str] = []
    real = auth.hashlib.scrypt

    def counted(*args, **kwargs):
        calls.append("kdf")
        return real(*args, **kwargs)

    monkeypatch.setattr(auth.hashlib, "scrypt", counted)
    db = SessionLocal()
    try:
        auth.issue_login_code(db, email)
        known = len(calls)
        calls.clear()
        assert auth.issue_login_code(db, f"nobody-{uuid.uuid4().hex[:8]}@example.invalid") is None
        unknown = len(calls)
    finally:
        db.close()
    assert known == unknown >= 1, f"a known address ran {known} KDFs, an unknown one {unknown}"
