from pydantic import BaseModel


class ContentRecord(BaseModel):
    id: int
    title: str
    body: str
    status: str = "active"


class Category(BaseModel):
    id: int
    name: str
    type: str = "main"


class ContentCategoryAssignment(BaseModel):
    id: int
    content_id: int
    category_id: int
    score: int = 10

class ContentCreate(BaseModel):
    title: str
    body: str