from datetime import datetime

from pydantic import BaseModel, Field


class Asset(BaseModel):
    """One library image (ADR-197). `reference` is what an image field stores;
    `url` is where it is served, publicly (point 11)."""

    id: int
    #: Whose library it is: the picker lists the brands a person may see.
    brand_id: int
    name: str
    label: str
    product_id: str | None = None
    media_type: str
    size_bytes: int
    width: int
    height: int
    alt_text: str
    reference: str
    url: str
    hidden: bool
    created_at: datetime
    updated_at: datetime


class AssetDescribe(BaseModel):
    alt_text: str = Field("", max_length=500)
