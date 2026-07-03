from datetime import datetime

from pydantic import BaseModel


class AudienceGroup(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class AudienceGroupCreate(BaseModel):
    name: str
    description: str | None = None


class AudienceGroupMember(BaseModel):
    id: int
    group_id: int
    recipient_id: int
    added_at: datetime
