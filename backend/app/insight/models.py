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