"""Unsubscribe: the link in every marketing email, and the opt-out it makes
(ADR-191; ADR-169 point 1 — a route, not a flow).

The link holds a random token stored with the delivered message, so the
message itself says who, which brand, which channel and which purpose. The
opt-out is an ordinary consent event (source "unsubscribe"), so the send-time
exclusion stack honours it with no new mechanism (ADR-163).
"""
import os
import secrets
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.auth.db_models import BrandDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.recipients.consent import MARKETING, latest_consent_status, record_consent

#: Where recipients reach the unsubscribe page. In development the API serves
#: it itself; a deployment sets its public address.
PUBLIC_BASE_URL_DEFAULT = "http://localhost:8000"
SOURCE = "unsubscribe"
OPTED_OUT = "opted_out"


def public_base_url() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or PUBLIC_BASE_URL_DEFAULT).rstrip("/")


def public_base_url_problem() -> str | None:
    """Why the configured address cannot go into a real mail, or None.

    The link is fixed into each mail when it is sent and can never be
    corrected afterwards (ADR-191), so a real send needs an address set on
    purpose, reachable over https. The development default fails this on
    purpose: it only works on this machine (task-330)."""
    configured = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    if not configured:
        return "PUBLIC_BASE_URL is not set, so the unsubscribe link would point at this machine"
    parts = urlsplit(configured)
    if parts.scheme != "https" or not parts.hostname:
        return f"PUBLIC_BASE_URL must be an https address with a host, not {configured!r}"
    return None


def unsubscribe_path(token: str) -> str:
    return f"/unsubscribe/{token}"


def unsubscribe_url(token: str) -> str:
    return public_base_url() + unsubscribe_path(token)


def footer_for(db: Session, execution: DeliveryExecutionDB, send_instance: SendInstanceDB) -> dict | None:
    """The link this message carries, minting its token on first use — or
    None for a message that carries none (not email, or not marketing).

    Returned as plain data because it is also recorded in the delivery record:
    a reconstruction (ADR-183) must render the same footer, even after the
    brand is renamed."""
    if execution.channel != "email" or execution.purpose != MARKETING:
        return None
    if not execution.unsubscribe_token:
        execution.unsubscribe_token = secrets.token_urlsafe(32)
    brand = db.get(BrandDB, send_instance.brand_id)
    return {"url": unsubscribe_url(execution.unsubscribe_token), "brand": brand.name if brand else ""}


def message_for(db: Session, token: str) -> tuple[DeliveryExecutionDB, BrandDB] | None:
    """The delivered message a token names, and the brand that sent it."""
    if not token or len(token) > 64:
        return None
    row = (
        db.query(DeliveryExecutionDB, BrandDB)
        .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
        .join(BrandDB, BrandDB.id == SendInstanceDB.brand_id)
        .filter(DeliveryExecutionDB.unsubscribe_token == token)
        .first()
    )
    return (row[0], row[1]) if row else None


def _opt_out(db: Session, recipient_id: int, brand_id: int, channel: str, execution_id: int) -> bool:
    """One cell, written only if it is not opted out already, so a repeated
    click or one-click POST adds nothing. It records the delivery the link
    came from, so the send can count it (ADR-196 point 6)."""
    if latest_consent_status(db, recipient_id, brand_id, channel=channel, purpose=MARKETING) == OPTED_OUT:
        return False
    record_consent(db, recipient_id, OPTED_OUT, brand_id, source=SOURCE, channel=channel,
                   purpose=MARKETING, commit=False, delivery_execution_id=execution_id)
    return True


def unsubscribe(db: Session, token: str, *, everything: bool = False) -> tuple[BrandDB, bool] | None:
    """Opt the message's recipient out. Returns (sending brand, whether
    everything was opted out), or None for a token that names no message.

    The default is marketing on the message's channel from the sending brand
    (ADR-163 addendum 2026-09-15 point 2). `everything` — marketing from every
    brand on every channel — is honoured only while the company setting offers
    it (ADR-191 point 4); otherwise the default applies. Transactional messages
    are never touched: only the marketing purpose is written."""
    from app.channels.registry import list_channels
    from app.settings.service import get_unsubscribe_offer_everything

    found = message_for(db, token)
    if found is None:
        return None
    execution, brand = found
    everything = everything and get_unsubscribe_offer_everything(db)
    if everything:
        for brand_id in [b.id for b in db.query(BrandDB.id)]:
            for channel in list_channels():
                _opt_out(db, execution.recipient_id, brand_id, channel.name, execution.id)
    else:
        _opt_out(db, execution.recipient_id, brand.id, execution.channel, execution.id)
    db.commit()
    return brand, everything
