from datetime import datetime

from pydantic import BaseModel


class DeliveryExecution(BaseModel):
    id: int
    send_instance_id: int
    recipient_id: int
    status: str
    provider: str | None = None
    provider_message_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DeliveryExecutionCreate(BaseModel):
    send_instance_id: int
    recipient_id: int
    status: str = "created"
    provider: str | None = None
    provider_message_id: str | None = None


class SendInstance(BaseModel):
    id: int
    snapshot_id: int
    name: str
    status: str
    provider: str | None = None
    scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SendInstanceCreate(BaseModel):
    snapshot_id: int
    name: str
    status: str = "draft"
    provider: str | None = None
    scheduled_at: datetime | None = None