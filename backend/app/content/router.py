from fastapi import APIRouter

from app.content.models import ContentRecord, Category
from app.content.service import (
    list_content_records,
    list_categories,
    list_categories_for_content,
)


router = APIRouter(prefix="/content", tags=["content"])


@router.get("/", response_model=list[ContentRecord])
def get_content_records():
    return list_content_records()


@router.get("/categories", response_model=list[Category])
def get_categories():
    return list_categories()


@router.get("/{content_id}/categories", response_model=list[Category])
def get_content_categories(content_id: int):
    return list_categories_for_content(content_id)