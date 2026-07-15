from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ContentOverrideCreate(BaseModel):
    module_instance_id: int
    # The only accepted override kind today: field-level edits to the resolved
    # content (Cases 1 & 3). Keys are validated against the module's manifest.
    field_overrides: dict[str, Any] | None = None
    # Record swaps are reserved for Case 2 (category-scoped) and rejected for
    # now — kept on the input shape so the error can explain why, rather than
    # silently dropping the field.
    override_content_record_id: int | None = None
    # The system's own pick, recorded for the trust-loop comparison.
    system_content_record_id: int | None = None
    send_instance_id: int | None = None
    overridden_by: str
    reason: str | None = None


class ContentOverride(BaseModel):
    id: int
    module_instance_id: int
    field_overrides: dict[str, Any] | None
    override_content_record_id: int | None
    condition_category_id: int | None
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
