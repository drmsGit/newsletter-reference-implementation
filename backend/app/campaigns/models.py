from datetime import datetime
from pydantic import BaseModel
from typing import Any


class Variant(BaseModel):
    id: int
    campaign_id: int
    name: str
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class VariantCreate(BaseModel):
    name: str = "Variant A"
    status: str = "draft"


class Campaign(BaseModel):
    id: int
    name: str
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    name: str
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
    position: int
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


class DecisionResolution(BaseModel):
    id: int
    decision_slot_id: int
    content_record_id: int
    reason: str | None = None
    score: int | None = None
    created_at: datetime


class DecisionResolutionCreate(BaseModel):
    content_record_id: int
    reason: str | None = None
    score: int | None = None