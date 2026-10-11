from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field



class ProfileFieldOut(BaseModel):
    """One field a profile may hold, as `storage/brand_profile.json` declares it."""

    name: str
    type: str = Field(description="colour, font_family, size, image, text, url or number")
    label: str
    group: str
    multiline: bool
    core: bool = Field(description="One of the fields the platform itself relies on (ADR-194 point 3)")
    required_for: list[str] = Field(
        description="The profile kinds that cannot send without it: marketing, transactional")


class BrandProfileSummary(BaseModel):
    id: int
    name: str
    language: str
    kind: str
    is_default: bool
    complete: bool = Field(description="Whether an email may use it: no required field is missing")
    missing: list[str] = Field(description="The required fields still empty, in the structure's order")
    updated_at: datetime = Field(description="The version token for If-Match")


class BrandProfile(BrandProfileSummary):
    field_values: dict[str, Any]
    may_manage: bool = Field(
        False, description="Whether this reader may write: a person holding brand_profiles.manage "
                           "in the working brand. A machine never may. Like the settings "
                           "screen's; the list carries none, because a paged list has one "
                           "shape (ADR-185 point 2).")


class BrandProfileCreate(BaseModel):
    name: str
    language: str = "en"
    kind: str = Field("marketing", description="marketing; transactional is refused until task-355")
    field_values: dict[str, Any] = Field(default_factory=dict)


class BrandProfileUpdate(BaseModel):
    """A full replace of the name and values. Language and kind stay as they
    are when left out."""

    name: str
    language: str | None = None
    kind: str | None = None
    field_values: dict[str, Any] = Field(default_factory=dict)


class BrandProfileDuplicate(BaseModel):
    name: str | None = Field(None, description='Left out: "<name> (copy)", numbered when taken')


class BrandProfileDeleted(BaseModel):
    variants_moved: int = Field(description="Variants that used it and now use the default")
