from datetime import datetime

from pydantic import BaseModel


class DeliveryExecution(BaseModel):
    id: int
    snapshot_id: int
    recipient_id: str
    status: str
    provider: str | None = None
    provider_message_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DeliveryExecutionCreate(BaseModel):
    snapshot_id: int
    recipient_id: str
    status: str = "created"
    provider: str | None = None
    provider_message_id: str | None = None