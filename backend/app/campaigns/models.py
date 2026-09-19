from datetime import datetime
from pydantic import BaseModel
from typing import Any


class Variant(BaseModel):
    id: int
    campaign_id: int
    # ADR-160 point 4. Fixed at creation (point 5), so there is no setter for
    # it anywhere and `VariantUpdate` deliberately does not carry it.
    channel: str
    name: str
    subject: str | None = None
    preheader: str | None = None
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class VariantCreate(BaseModel):
    channel: str = "email"
    name: str = "Variant A"
    subject: str | None = None
    preheader: str | None = None
    status: str = "draft"


class VariantUpdate(BaseModel):
    name: str
    subject: str | None = None
    preheader: str | None = None


class Campaign(BaseModel):
    id: int
    name: str
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    name: str
    # The channel of the initial variant this creates, not a property of the
    # campaign — ADR-160 point 4 keeps channel off the campaign. Defaulted here
    # and only here: an unauthenticated machine caller has no session to have
    # chosen from, while `create_campaign` itself still refuses to guess.
    channel: str = "email"
    status: str = "draft"
    initial_variant_name: str = "Variant A"


class CampaignWithVariants(Campaign):
    variants: list[Variant]


class ModuleInstance(BaseModel):
    id: int
    variant_id: int
    module_type: str
    position: int
    content_record_id: int | None = None
    module_data: dict[str, Any] | None = None
    decision_slot_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ModuleInstanceCreate(BaseModel):
    module_type: str
    content_record_id: int | None = None
    module_data: dict[str, Any] | None = None
    decision_slot_id: int | None = None


class DecisionSlot(BaseModel):
    id: int
    variant_id: int
    name: str
    decision_type: str
    decision_strategy: str
    candidate_filter: dict[str, Any] | None = None
    strategy_config: dict[str, Any] | None = None
    max_results: int = 1
    created_at: datetime
    updated_at: datetime


class DecisionSlotCreate(BaseModel):
    name: str
    decision_type: str = "content_recommendation"
    decision_strategy: str = "top_score"
    candidate_filter: dict[str, Any] | None = None
    strategy_config: dict[str, Any] | None = None
    max_results: int = 1


class ModuleInstanceUpdate(BaseModel):
    """Edit a module in place.

    Mirrors `ModuleInstanceCreate` minus `position`, which moves through its
    own endpoint because reordering is a different act from editing and has a
    uniqueness constraint of its own.
    """

    module_type: str
    content_record_id: int | None = None
    module_data: dict[str, Any] | None = None
    decision_slot_id: int | None = None


class DecisionSlotUpdate(BaseModel):
    """Edit a slot's strategy and configuration.

    `name`, `decision_type` and `max_results` are deliberately absent: the
    service updates strategy, candidate filter and config only, and accepting
    fields it will silently drop would be worse than not offering them.
    """

    decision_strategy: str
    candidate_filter: dict[str, Any] | None = None
    strategy_config: dict[str, Any] | None = None


class DecisionResolution(BaseModel):
    id: int
    decision_slot_id: int
    recipient_id: int | None = None
    content_record_id: int
    content_version_id: int | None = None
    reason: str | None = None
    score: float | None = None
    created_at: datetime


class DecisionResolutionCreate(BaseModel):
    recipient_id: int | None = None
    content_record_id: int
    content_version_id: int | None = None
    reason: str | None = None
    score: float | None = None