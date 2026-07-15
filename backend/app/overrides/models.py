from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ContentOverrideCreate(BaseModel):
    module_instance_id: int
    # At least one of these two must be set (enforced in the service): a
    # record-level pin and/or field-level edits.
    override_content_record_id: int | None = None
    field_overrides: dict[str, Any] | None = None
    # The system's own pick, recorded for the trust-loop comparison.
    system_content_record_id: int | None = None
    send_instance_id: int | None = None
    overridden_by: str
    reason: str | None = None


class ContentOverride(BaseModel):
    id: int
    module_instance_id: int
    override_content_record_id: int | None
    field_overrides: dict[str, Any] | None
    system_content_record_id: int | None
    send_instance_id: int | None
    overridden_by: str
    reason: str | None
    active: bool
    reverted_at: datetime | None
    outcome_delta: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutcomeDeltaUpdate(BaseModel):
    outcome_delta: dict[str, Any]
