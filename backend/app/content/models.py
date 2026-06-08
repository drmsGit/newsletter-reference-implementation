from pydantic import BaseModel


class ContentRecord(BaseModel):
    id: int
    title: str
    body: str
    status: str = "active"


class ContentCreate(BaseModel):
    title: str
    body: str


class Category(BaseModel):
    id: int
    name: str
    type: str = "main"
    parent_category_id: int | None = None


class CategoryCreate(BaseModel):
    name: str
    type: str = "main"
    parent_category_id: int | None = None


class ContentCategoryAssignment(BaseModel):
    id: int
    content_id: int
    category_id: int
    score: int = 10


class ContentCategoryAssignmentCreate(BaseModel):
    category_id: int
    score: int = 10