"""A sign-in request takes the same time whether or not the address exists.

task-5, ADR-151 §2. Both sign-in routes already answered identically — same
status, same body — for a known address and an unknown one. But a known
address used to call the mail provider inline, over HTTPS, before the answer
went back, so the identical response arrived hundreds of milliseconds later
when the account existed. The code is now issued in the request and SENT after
the response.

**These tests run a real uvicorn server, deliberately.** Starlette's
`TestClient` runs background tasks before it hands back the response, so under
it a route that sends inline and a route that sends afterwards take exactly the
same time — the property under test is invisible there. A real server returns
the response first. Delivery is patched to take half a second, so a route that
waits for it is unmistakable against a response that takes milliseconds.
"""
import re
import socket
import threading
import time
import uuid

import httpx
import pytest
import uvicorn
from sqlalchemy import text

import app.auth.router as auth_router
from app.auth import service as auth
from app.database import SessionLocal
from main import app

SLOW = 0.5
#: A route that waited for delivery takes at least SLOW. Half of it is far above
#: a real response here (tens of milliseconds) and far below the send.
WAITED = SLOW / 2


@pytest.fixture
def sends(monkeypatch):
    """Delivery that takes SLOW seconds and records what it sent.

    Patched on the router module, because that is the name the routes call;
    patching the service would not reach them.
    """
    delivered: list[tuple[str, str]] = []

    def slow_deliver(address, code):
        time.sleep(SLOW)
        delivered.append((address, code))

    monkeypatch.setattr(auth_router, "deliver_code", slow_deliver)
    return delivered


@pytest.fixture
def known():
    db = SessionLocal()
    email = f"timing-{uuid.uuid4().hex[:8]}@example.invalid"
    user = auth.create_user(db, email=email, role_key="viewer")
    try:
        yield email
    finally:
        db.rollback()
        db.execute(text("DELETE FROM login_codes WHERE user_id = :u"), {"u": user.id})
        for table in ("auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.commit()
        db.close()


@pytest.fixture
def server():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    with SessionLocal() as db:
        # The database's clock, not ours: the throttle rows are stamped by
        # `server_default=now()`, so this is the boundary they are compared to.
        started_at = db.execute(text("SELECT now()")).scalar()
    instance = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not instance.started:
        assert time.monotonic() < deadline, "uvicorn did not start"
        time.sleep(0.02)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        instance.should_exit = True
        thread.join(timeout=5)
        # The throttle counts requests per address and per client, and stores
        # both as hashes — so clear by time what this server received, or the
        # next test from 127.0.0.1 inherits its budget.
        with SessionLocal() as db:
            db.execute(
                text("DELETE FROM login_code_requests WHERE created_at >= :t"),
                {"t": started_at},
            )
            db.commit()


def _form_request(base, email, client=None):
    client = client or httpx.Client()
    form = client.get(f"{base}/ui/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', form.text)
    data = {"email": email, **({"csrf_token": token.group(1)} if token else {})}
    started = time.perf_counter()
    response = client.post(f"{base}/ui/login", data=data, follow_redirects=False)
    return time.perf_counter() - started, response


def _json_request(base, email, client=None):
    client = client or httpx.Client()
    started = time.perf_counter()
    response = client.post(f"{base}/auth/session/request", json={"email": email})
    return time.perf_counter() - started, response


def _wait_for(sends, address):
    deadline = time.monotonic() + SLOW * 4
    while time.monotonic() < deadline:
        if any(a == address for a, _ in sends):
            return
        time.sleep(0.05)
    raise AssertionError(f"no code was ever sent to {address}")


@pytest.mark.parametrize("route", [_form_request, _json_request], ids=["form", "json"])
class TestTheResponseDoesNotWaitForTheSend:

    def test_a_known_address_is_answered_before_its_code_is_sent(self, route, server, known, sends):
        elapsed, response = route(server, known)

        assert response.status_code in (202, 303), response.text
        assert elapsed < WAITED, (
            f"a known address took {elapsed * 1000:.0f} ms to answer against a "
            f"{SLOW * 1000:.0f} ms send — the route waited for delivery, and the "
            "delay tells anyone timing it that the account exists"
        )
        # And it was still sent. A route that answers fast because it never
        # sends would pass the assertion above and lock everybody out.
        _wait_for(sends, auth.normalise_email(known))

    def test_the_code_sent_afterwards_signs_in(self, route, server, known, sends):
        """The code delivered in the background is the live one — issued in the
        request, committed before the response, and not superseded by anything
        the background step does."""
        route(server, known)
        _wait_for(sends, auth.normalise_email(known))
        _, code = next(s for s in sends if s[0] == auth.normalise_email(known))

        with SessionLocal() as db:
            assert auth.verify_login_code(db, known, code) is not None

    def test_an_unknown_address_schedules_nothing(self, route, server, sends):
        stranger = f"nobody-{uuid.uuid4().hex[:8]}@example.invalid"

        route(server, stranger)
        time.sleep(SLOW + 0.2)

        assert sends == []


def test_reusing_the_connection_does_not_expose_the_send(server, known, sends):
    """The side door, checked rather than assumed. If the server held the next
    request on a kept-alive connection until the previous one's background
    task finished, sending a sign-in request and then anything else on the
    same connection would measure the send — the oracle back again."""
    with httpx.Client() as kept:
        _json_request(server, known, client=kept)
        started = time.perf_counter()
        kept.get(f"{server}/ui/login")
        follow = time.perf_counter() - started

    assert follow < WAITED, (
        f"the next request on the same connection took {follow * 1000:.0f} ms — "
        "it waited for the background send"
    )
    _wait_for(sends, auth.normalise_email(known))
