from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.content.models import ContentRecord, Category
from app.content.service import (
    list_content_records,
    list_categories,
    list_categories_for_content,
)


router = APIRouter(prefix="/content", tags=["content"])


@router.get("/", response_model=list[ContentRecord])
def get_content_records(db: Session = Depends(get_db)):
    return list_content_records(db)


@router.get("/categories", response_model=list[Category])
def get_categories(db: Session = Depends(get_db)):
    return list_categories(db)


@router.get("/{content_id}/categories", response_model=list[Category])
def get_content_categories(content_id: int, db: Session = Depends(get_db)):
    return list_categories_for_content(db, content_id)