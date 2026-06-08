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
    created_at: datetime
    updated_at: datetime


class ModuleInstanceCreate(BaseModel):
    module_type: str
    position: int
    content_record_id: int | None = None
    module_data: dict[str, Any] | None = None