from datetime import datetime

from pydantic import BaseModel


class Campaign(BaseModel):
    id: int
    name: str
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    name: str
    status: str = "draft"