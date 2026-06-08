from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.content.models import (
    ContentRecord,
    ContentCreate,
    Category,
    CategoryCreate,
    ContentCategoryAssignment,
    ContentCategoryAssignmentCreate,
)
from app.content.service import (
    list_content_records,
    list_categories,
    list_categories_for_content,
    create_content,
    create_category,
    assign_category_to_content,
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

@router.post("/", response_model=ContentRecord)
def create_content_record(
    payload: ContentCreate,
    db: Session = Depends(get_db),
):
    return create_content(
        db=db,
        title=payload.title,
        body=payload.body,
    )

@router.post("/categories", response_model=Category)
def create_category_record(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
):
    return create_category(
        db=db,
        name=payload.name,
        type=payload.type,
        parent_category_id=payload.parent_category_id,
    )


@router.post("/{content_id}/categories", response_model=ContentCategoryAssignment)
def assign_category(
    content_id: int,
    payload: ContentCategoryAssignmentCreate,
    db: Session = Depends(get_db),
):
    assignment = assign_category_to_content(
        db=db,
        content_id=content_id,
        category_id=payload.category_id,
        score=payload.score,
    )

    return ContentCategoryAssignment(
        id=assignment.id,
        content_id=assignment.content_id,
        category_id=assignment.category_id,
        score=assignment.score,
    )