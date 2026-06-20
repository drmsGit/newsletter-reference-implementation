from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EngagementEvent(BaseModel):
    id: int
    delivery_execution_id: int
    event_type: str
    provider: str | None = None
    provider_event_id: str | None = None
    event_data: dict[str, Any] | None = None
    occurred_at: datetime
    created_at: datetime


class EngagementEventCreate(BaseModel):
    delivery_execution_id: int
    event_type: str
    provider: str | None = None
    provider_event_id: str | None = None
    event_data: dict[str, Any] | None = None
    occurred_at: datetime | None = None


class PreferenceUpdateResult(BaseModel):
    event_id: int
    recipient_id: int
    content_record_id: int
    updated_categories: list[int]
    applied_deltas: dict[int, float]