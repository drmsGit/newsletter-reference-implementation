"""Resend outbound adapter — one worked example of a real ESP behind the
`DeliveryProvider` contract (ADR-100/101), proving the "no vendor lock-in" claim.

Credentials come from the environment, never code or the DB:
  RESEND_API_KEY   your Resend API key (re_...)          [required to send]
  RESEND_FROM      verified sender, e.g. "News <news@yourdomain.com>"
                   (defaults to Resend's onboarding@resend.dev sandbox sender,
                    which only delivers to your own account email until your
                    domain's DNS is verified)

The adapter builds the request and maps the response to a SendResult; it never
raises for a send failure (network error, unverified domain, bad key) — it
returns success=False with the provider's message, so the send loop records an
accurate "failed" status instead of crashing (ADR-086 spirit, Delivery Q6).
"""
import logging
import os

import httpx

from app.delivery.providers.base import DeliveryProvider, SendResult

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "onboarding@resend.dev"


class ResendProvider(DeliveryProvider):
    def __init__(self, api_key: str | None = None, from_address: str | None = None):
        self.api_key = api_key if api_key is not None else os.environ.get("RESEND_API_KEY")
        self.from_address = from_address or os.environ.get("RESEND_FROM", DEFAULT_FROM)

    def send(self, recipient_email: str, subject: str, html: str) -> SendResult:
        if not self.api_key:
            return SendResult(success=False, message="RESEND_API_KEY is not set")

        payload = {
            "from": self.from_address,
            "to": [recipient_email],
            "subject": subject,
            "html": html,
        }
        try:
            response = httpx.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15.0,
            )
        except httpx.HTTPError as error:
            logger.warning("resend send network error: %s", error)
            return SendResult(success=False, message=f"network error: {error}")

        if response.status_code == 200:
            message_id = response.json().get("id")
            logger.info("resend send ok: to=%s id=%s", recipient_email, message_id)
            return SendResult(success=True, provider_message_id=message_id, message="accepted")

        # Resend errors come back as JSON like {"statusCode","name","message"}.
        try:
            detail = response.json().get("message") or response.text
        except ValueError:
            detail = response.text
        logger.warning("resend send failed: HTTP %s — %s", response.status_code, detail)
        return SendResult(success=False, message=f"HTTP {response.status_code}: {detail}")
