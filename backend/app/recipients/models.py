from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Recipient(BaseModel):
    id: int
    external_id: str
    email: str
    language: str | None = None
    preferred_airport: str | None = None
    attributes: dict[str, Any] | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class RecipientCreate(BaseModel):
    external_id: str
    email: str
    language: str | None = None
    preferred_airport: str | None = None
    attributes: dict[str, Any] | None = None
    status: str = "active"