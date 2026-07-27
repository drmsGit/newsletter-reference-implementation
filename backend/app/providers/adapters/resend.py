"""Resend inbound (webhook) adapter — the one worked example of turning a raw
provider webhook into the canonical internal event shape (`ProviderEventCreate`),
the inbound mirror of the outbound `DeliveryProvider` contract.

Deliberately small and Resend-specific rather than a generic auto-fitting layer
(see the inbound-adapter backlog item): real webhook payloads differ enough per
ESP — signature scheme, event names, field layout — that "adjust this file to
your provider" beats one contract that pretends to fit them all. A new provider
copies this file and changes three things: the signature check, the event-name
map, and the field paths.

Credentials/secrets come from the environment, never code or the DB:
  RESEND_WEBHOOK_SECRET   Svix signing secret ("whsec_…") from the Resend
                          dashboard. If unset, signature verification is
                          SKIPPED (local testing only — never in production).
"""
import base64
import hashlib
import hmac
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Resend event name → canonical internal event_type. Only "open"/"click" are
# content-tied (they move per-category signals, ADR-132); the rest are delivery
# status / feedback that the insight + consent layers consume differently.
RESEND_EVENT_TYPE_MAP = {
    "email.opened": "open",
    "email.clicked": "click",
    "email.delivered": "delivered",
    "email.bounced": "bounce",
    "email.complained": "complaint",
    "email.delivery_delayed": "deferred",
}


@dataclass
class NormalizedEvent:
    """Canonical shape ingest_provider_event expects — provider-agnostic."""
    provider: str
    provider_message_id: str
    event_type: str
    provider_event_id: str
    event_data: dict


def verify_signature(raw_body: bytes, headers: dict) -> bool:
    """Verify a Resend/Svix webhook signature. Returns True (allow) when no
    secret is configured, so the pipeline is testable locally without one —
    a warning is logged so this can't silently ship to production."""
    secret = os.environ.get("RESEND_WEBHOOK_SECRET")
    if not secret:
        logger.warning("RESEND_WEBHOOK_SECRET unset — skipping webhook signature verification (dev only)")
        return True

    # Svix headers (case-insensitive lookup).
    lower = {k.lower(): v for k, v in headers.items()}
    svix_id = lower.get("svix-id")
    svix_timestamp = lower.get("svix-timestamp")
    svix_signature = lower.get("svix-signature")
    if not (svix_id and svix_timestamp and svix_signature):
        logger.warning("missing svix-* headers on webhook — rejecting")
        return False

    # Secret is "whsec_<base64>"; the HMAC key is the decoded base64 part.
    secret_key = base64.b64decode(secret.split("_", 1)[1] if "_" in secret else secret)
    signed_content = f"{svix_id}.{svix_timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = base64.b64encode(hmac.new(secret_key, signed_content, hashlib.sha256).digest()).decode()

    # The header is a space-separated list of "v1,<sig>" — match any, in
    # constant time.
    for part in svix_signature.split():
        _, _, sig = part.partition(",")
        if hmac.compare_digest(sig, expected):
            return True
    logger.warning("webhook signature mismatch — rejecting")
    return False


def parse_webhook(payload: dict) -> NormalizedEvent | None:
    """Map a Resend webhook body to a NormalizedEvent, or None if it's an event
    type we don't handle. Resend shape: {type, created_at, data:{email_id,…}}."""
    resend_type = payload.get("type")
    event_type = RESEND_EVENT_TYPE_MAP.get(resend_type)
    if event_type is None:
        logger.info("ignoring unmapped Resend event type: %s", resend_type)
        return None

    data = payload.get("data") or {}
    provider_message_id = data.get("email_id") or data.get("id") or ""
    if not provider_message_id:
        logger.warning("Resend %s event has no email_id — cannot correlate", resend_type)
        return None

    # Resend doesn't send a stable event id in the body; derive a
    # deterministic one so redelivery of the *same* event dedupes (ADR: a
    # webhook delivered twice must not double-count). email_id + type +
    # created_at is unique per real event.
    provider_event_id = f"{provider_message_id}:{resend_type}:{payload.get('created_at', '')}"

    return NormalizedEvent(
        provider="resend",
        provider_message_id=provider_message_id,
        event_type=event_type,
        provider_event_id=provider_event_id,
        event_data=payload,
    )
