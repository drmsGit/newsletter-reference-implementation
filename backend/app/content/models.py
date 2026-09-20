from pydantic import BaseModel
from datetime import datetime
from typing import Any


class ContentRecord(BaseModel):
    id: int
    title: str
    description: str | None = None
    content: dict[str, Any]
    status: str = "active"


class ContentCreate(BaseModel):
    title: str
    description: str | None = None
    content: dict[str, Any]


class ContentPatch(BaseModel):
    """A partial edit that honours what the caller was offering.

    **`groups` is the field this exists for.** An absent field and a cleared
    one are indistinguishable in a dict, so a client that renders push fields
    only when push is enabled would erase push copy on every edit made while
    it was off — unless it can say which groups it was authoritative for.
    The Jinja form has carried that signal since 2026-09-17 as
    `channel_sections_present`; this is the same signal on the JSON plane.

    Omitting `groups` merges nothing and is a no-op on `content`, which is the
    safe default: a caller that has not said what it was offering has not
    earned the right to clear anything.
    """

    title: str | None = None
    description: str | None = None
    content: dict[str, Any] = {}
    #: Names from `content.service.CONTENT_FIELD_GROUPS` — "email", "push".
    groups: list[str] = []


class ContentStatusUpdate(BaseModel):
    status: str


class Category(BaseModel):
    id: int
    name: str
    type: str = "main"


class CategoryCreate(BaseModel):
    name: str
    type: str = "main"


class ContentCategoryAssignment(BaseModel):
    id: int
    content_id: int
    category_id: int
    score: int = 10


class ContentCategoryAssignmentCreate(BaseModel):
    category_id: int
    score: int = 10


class ContentVersion(BaseModel):
    id: int
    content_record_id: int
    version_number: int
    content: dict[str, Any]
    created_by: str | None = None
    created_at: datetime


class ContentVersionCreate(BaseModel):
    content_record_id: int
    created_by: str | None = None


class CategoryRelation(BaseModel):
    id: int
    parent_category_id: int
    child_category_id: int
    relation_type: str = "parent_child"
    created_at: datetime


class CategoryRelationCreate(BaseModel):
    parent_category_id: int
    child_category_id: int
    relation_type: str = "parent_child"