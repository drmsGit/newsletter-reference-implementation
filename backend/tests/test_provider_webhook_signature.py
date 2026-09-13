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

from app.providers.adapters.resend import verify_signature

SECRET = "whsec_" + base64.b64encode(b"test-signing-key-0123456789").decode()
BODY = b'{"type":"email.clicked","data":{"email_id":"abc-123"}}'
SVIX_ID = "msg_test_1"
SVIX_TS = "1700000000"


def _signed_headers(secret: str = SECRET, body: bytes = BODY) -> dict:
    key = base64.b64decode(secret.split("_", 1)[1])
    signed = f"{SVIX_ID}.{SVIX_TS}.{body.decode()}".encode()
    sig = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return {
        "Svix-Id": SVIX_ID,
        "Svix-Timestamp": SVIX_TS,
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
