from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ConsentStatus(str, Enum):
    """CRM-sourced marketing consent. Only ``opted_in`` is treated as
    consenting at audience-resolution time; ``pending`` and ``opted_out``
    are filtered out before any decisioning/rendering runs."""

    opted_in = "opted_in"
    opted_out = "opted_out"
    pending = "pending"


class Recipient(BaseModel):
    id: int
    external_id: str
    email: str
    language: str | None = None
    attributes: dict[str, Any] | None = None
    status: str
    consent_status: ConsentStatus = ConsentStatus.pending
    created_at: datetime
    updated_at: datetime


class RecipientCreate(BaseModel):
    # Creating a recipient writes a consent event (source="import"), so it
    # carries the same requirement as a CRM assertion for the same reason.
    brand_id: int
    external_id: str
    # **`address` + `channel`, not `email`** — a breaking change to this
    # payload, made deliberately. ADR-167 settles that a push audience arrives
    # as ordinary contacts from the source system, so this route has to admit a
    # contact whose only contact point is a device token. An `email` alias was
    # rejected: this codebase is meant to be read, and an alias would teach the
    # shape the model no longer has. The route is part of the unauthenticated
    # JSON control plane gate 3 exists to close, so it has no external callers
    # by design.
    address: str = ""
    # What that address IS. Consent is recorded on this channel too, which is
    # the half that was silently wrong: a synced contact used to be granted
    # email consent whatever it had agreed to.
    channel: str = "email"
    language: str | None = None
    attributes: dict[str, Any] | None = None
    status: str = "active"
    consent_status: ConsentStatus = ConsentStatus.pending


class ConsentSyncRequest(BaseModel):
    """A consent assertion coming from the CRM for one recipient.

    **`brand_id` is required and has no default.** Consent is to a sender
    (ADR-163 addendum 2026-09-15), so an assertion that does not say which
    brand is not an assertion about consent — and defaulting it would land a
    grant nobody gave on whichever brand happens to be first. The CRM is the
    source of truth (ADR-120) and a company that has brands has the brand to
    send; a company with one brand has no brand field precisely because there
    is one brand, so it hardcodes the value — one constant in an integration it
    is writing anyway.

    `channel` and `purpose` default, because the grid's defaults are real
    defaults: an assertion that says nothing about channel is an assertion
    about email marketing, which is the only cell that exists today. Brand has
    no such honest default.
    """

    consent_status: ConsentStatus
    brand_id: int
    source: str = "crm"
    channel: str = "email"
    purpose: str = "marketing"
    note: str | None = None


class ConsentSyncLog(BaseModel):
    """One conversation with the CRM — that it ran, whether it succeeded, how
    much it changed. It carries no consent values: those are consent events
    with `source="crm"` (ADR-163 addendum 2026-09-12, point 2)."""

    id: int
    recipient_id: int | None = None
    external_id: str | None = None
    ok: bool
    changes_applied: int
    source: str
    note: str | None = None
    synced_at: datetime


class ConsentDriftDirection(str, Enum):
    """Which side moved, and therefore which way the correction flows."""

    # Something here opted the person out (usually a bounce or complaint) and
    # the CRM has not been told — relay it outward.
    platform_ahead = "platform_ahead"
    # The CRM asserted something that never took effect here — re-run the sync.
    crm_ahead = "crm_ahead"


class ConsentDriftItem(BaseModel):
    """A `(recipient, channel, purpose)` cell where the platform's effective
    consent disagrees with the CRM's last assertion."""

    recipient_id: int
    external_id: str
    email: str
    channel: str = "email"
    purpose: str = "marketing"
    platform_consent_status: ConsentStatus
    last_crm_consent_status: ConsentStatus
    last_synced_at: datetime
    direction: ConsentDriftDirection
    # What produced the platform's current state — "provider" on a bounce or
    # complaint, which is the common platform_ahead case.
    platform_source: str | None = None


class RecipientPreference(BaseModel):
    # A computed operational signal per category (ADR-132), not a stored row —
    # so no id/source/created_at. `score` is the decay-weighted signal.
    recipient_id: int
    category_id: int
    score: float


class RecipientPreferenceCreate(BaseModel):
    recipient_id: int
    category_id: int
    score: float
    source: str = "manual"