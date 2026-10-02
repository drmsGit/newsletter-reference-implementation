from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ContentOverrideCreate(BaseModel):
    """Create an override. **There is no author field** (task-243): who
    overrode is the authenticated caller, set by the server. A body that still
    sends `overridden_by` is not refused -- unknown fields are ignored -- and
    the value is never stored."""

    module_instance_id: int
    # Field-level edits to the resolved content — the only override kind. Keys
    # are validated against the module's manifest variables.
    field_overrides: dict[str, Any] | None = None
    # Which record the fields were applied to, for the trust-loop audit.
    system_content_record_id: int | None = None
    send_instance_id: int | None = None
    reason: str | None = None


class ContentOverride(BaseModel):
    id: int
    module_instance_id: int
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
