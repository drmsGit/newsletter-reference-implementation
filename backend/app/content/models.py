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