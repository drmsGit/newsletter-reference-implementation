from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.insight.models import EngagementEvent


class ProviderEventCreate(BaseModel):
    provider: str
    provider_message_id: str
    event_type: str
    provider_event_id: str
    event_data: dict[str, Any] = {}


class ProviderEventQuarantine(BaseModel):
    id: int
    provider: str
    provider_message_id: str
    event_type: str
    provider_event_id: str
    event_data: dict[str, Any] | None = None
    reason: str
    created_at: datetime


class ProviderEventIngestResult(BaseModel):
    status: str  # "matched" | "duplicate" | "quarantined"
    engagement_event: EngagementEvent | None = None
    quarantine: ProviderEventQuarantine | None = None