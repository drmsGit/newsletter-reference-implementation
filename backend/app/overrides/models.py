from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict


class OverrideType(str, Enum):
    content = "content"
    segment = "segment"


class OverrideEventCreate(BaseModel):
    override_type: OverrideType
    module_instance_id: int | None = None
    decision_slot_id: int | None = None
    send_instance_id: int | None = None
    system_content_record_id: int
    override_content_record_id: int
    overridden_by: str
    reason: str | None = None


class OverrideEvent(BaseModel):
    id: int
    override_type: OverrideType
    module_instance_id: int | None
    decision_slot_id: int | None
    send_instance_id: int | None
    system_content_record_id: int
    override_content_record_id: int
    overridden_by: str
    reason: str | None
    outcome_delta: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutcomeDeltaUpdate(BaseModel):
    outcome_delta: dict[str, Any]
