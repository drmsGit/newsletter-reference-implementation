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
    external_id: str
    email: str
    language: str | None = None
    attributes: dict[str, Any] | None = None
    status: str = "active"
    consent_status: ConsentStatus = ConsentStatus.pending


class ConsentSyncRequest(BaseModel):
    """A consent assertion coming from the CRM for one recipient."""

    consent_status: ConsentStatus
    source: str = "crm"
    note: str | None = None


class ConsentSyncLog(BaseModel):
    id: int
    recipient_id: int
    external_id: str
    crm_consent_status: ConsentStatus
    platform_status_before: ConsentStatus
    applied: bool
    source: str
    note: str | None = None
    synced_at: datetime


class ConsentDriftItem(BaseModel):
    """A recipient whose live platform consent_status disagrees with the most
    recent value the CRM asserted for them — i.e. a sync that never took."""

    recipient_id: int
    external_id: str
    email: str
    platform_consent_status: ConsentStatus
    last_crm_consent_status: ConsentStatus
    last_synced_at: datetime


class RecipientPreference(BaseModel):
    id: int
    recipient_id: int
    category_id: int
    score: float
    source: str
    created_at: datetime


class RecipientPreferenceCreate(BaseModel):
    recipient_id: int
    category_id: int
    score: float
    source: str = "manual"