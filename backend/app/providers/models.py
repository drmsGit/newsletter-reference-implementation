from typing import Any

from pydantic import BaseModel


class ProviderEventCreate(BaseModel):
    provider: str
    provider_message_id: str
    event_type: str
    provider_event_id: str
    event_data: dict[str, Any] = {}