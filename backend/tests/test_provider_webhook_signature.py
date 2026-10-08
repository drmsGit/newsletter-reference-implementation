"""Inbound webhook signature verification must fail CLOSED.

`POST /provider/webhooks/resend` is a public, unauthenticated endpoint: the
signature is the only thing standing between a stranger and the suppression
logic (forged bounces/complaints) and the signal layer (forged clicks). A
missing `RESEND_WEBHOOK_SECRET` is a configuration mistake, so it must reject
rather than allow. No DB, no network.
"""
import base64
import hashlib
import hmac
import time

from app.providers.adapters.resend import verify_signature

SECRET = "whsec_" + base64.b64encode(b"test-signing-key-0123456789").decode()
BODY = b'{"type":"email.clicked","data":{"email_id":"abc-123"}}'
SVIX_ID = "msg_test_1"
# Signed now: an event is only accepted within the tolerance of the current
# time (task-303). This was 1700000000 (November 2023), and it passed.
SVIX_TS = str(int(time.time()))


def _signed_headers(secret: str = SECRET, body: bytes = BODY, timestamp: str | None = None) -> dict:
    timestamp = timestamp or SVIX_TS
    key = base64.b64decode(secret.split("_", 1)[1])
    signed = f"{SVIX_ID}.{timestamp}.{body.decode()}".encode()
    sig = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return {
        "Svix-Id": SVIX_ID,
        "Svix-Timestamp": timestamp,
        "Svix-Signature": f"v1,{sig}",
    }


def test_rejects_when_secret_is_absent(monkeypatch):
    """The regression this file exists for: an unset secret used to return
    True (allow), turning a config mistake into open event ingestion."""
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    # Headers are a perfectly well-formed Svix set — the only defect is that
    # the server has no secret, so nothing can be verified against.
    assert verify_signature(BODY, _signed_headers()) is False


def test_rejects_when_secret_is_empty_string(monkeypatch):
    """An empty value in `.env` is the same configuration mistake."""
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "")
    assert verify_signature(BODY, _signed_headers()) is False


def test_accepts_a_correctly_signed_body(monkeypatch):
    """Guards the fix against the trivial 'always return False' regression."""
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    assert verify_signature(BODY, _signed_headers()) is True


def test_rejects_a_tampered_body(monkeypatch):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    headers = _signed_headers()
    assert verify_signature(BODY + b" ", headers) is False


def test_the_route_refuses_a_well_signed_event_while_the_secret_is_unset(monkeypatch):
    """task-98 item 5, at the route and not only the function: a request
    signed perfectly still gets nowhere when the server has no secret to check
    it against — the configuration mistake fails closed end to end."""
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    refused = client.post("/provider/webhooks/resend", content=BODY,
                          headers={**_signed_headers(), "Content-Type": "application/json"})
    assert refused.status_code == 401
    assert refused.json()["detail"] == "invalid webhook signature"

    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    admitted = client.post("/provider/webhooks/resend", content=BODY,
                           headers={**_signed_headers(), "Content-Type": "application/json"})
    assert admitted.status_code != 401, "the same request passes the door once the secret is set"


class TestAReplayedEventIsRefused:
    """task-303: a correctly signed event is accepted only within the
    tolerance of now (Svix's guidance, five minutes either way), so a captured
    genuine webhook cannot be sent again later. Deduplication already makes an
    exact replay of a stored event a no-op; this is the gate for everything it
    does not remember (a quarantined event, a pruned one)."""

    def test_an_old_signed_event_is_refused(self, monkeypatch):
        from app.providers.adapters.resend import WEBHOOK_TOLERANCE_SECONDS

        monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
        old = str(int(time.time()) - WEBHOOK_TOLERANCE_SECONDS - 60)
        assert verify_signature(BODY, _signed_headers(timestamp=old)) is False
        assert verify_signature(BODY, _signed_headers(timestamp="1700000000")) is False

    def test_a_signed_event_from_the_future_is_refused(self, monkeypatch):
        from app.providers.adapters.resend import WEBHOOK_TOLERANCE_SECONDS

        monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
        ahead = str(int(time.time()) + WEBHOOK_TOLERANCE_SECONDS + 60)
        assert verify_signature(BODY, _signed_headers(timestamp=ahead)) is False

    def test_a_signed_event_within_the_window_is_accepted(self, monkeypatch):
        monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
        assert verify_signature(BODY, _signed_headers(timestamp=str(int(time.time()) - 60))) is True
        assert verify_signature(BODY, _signed_headers(timestamp=str(int(time.time()) + 60))) is True

    def test_a_timestamp_that_is_not_a_number_is_refused(self, monkeypatch):
        monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
        assert verify_signature(BODY, _signed_headers(timestamp="yesterday")) is False
