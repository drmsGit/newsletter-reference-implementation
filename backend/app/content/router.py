from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.content.models import (
    ContentRecord,
    ContentCreate,
    Category,
    CategoryCreate,
    CategoryRelation,
    CategoryRelationCreate,
    ContentCategoryAssignment,
    ContentCategoryAssignmentCreate,
    ContentVersion,
    ContentVersionCreate,
)
from app.content.service import (
    list_content_records,
    get_content_record,
    to_content_record,
    update_content_record,
    list_categories,
    list_categories_for_content,
    create_content,
    create_category,
    create_category_relation,
    list_category_relations,
    list_parent_relations_for_category,
    list_child_relations_for_category,
    assign_category_to_content,
    create_content_version,
    list_versions_for_content,
)


router = APIRouter(prefix="/content", tags=["content"])


@router.get("/", response_model=list[ContentRecord])
def get_content_records(db: Session = Depends(get_db)):
    return list_content_records(db)


# These fixed-path routes (/categories, /category-relations) must be
# registered before /{content_id} below — FastAPI matches routes in
# registration order, so a parameterized route registered first would
# otherwise swallow these paths (e.g. "categories" parsed as content_id
# and failing int validation) rather than ever reaching them.
@router.get("/categories", response_model=list[Category])
def get_categories(db: Session = Depends(get_db)):
    return list_categories(db)


@router.get("/category-relations", response_model=list[CategoryRelation])
def get_category_relations(db: Session = Depends(get_db)):
    return list_category_relations(db)


@router.get("/{content_id}", response_model=ContentRecord)
def get_content_record_by_id(content_id: int, db: Session = Depends(get_db)):
    record = get_content_record(db, content_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return to_content_record(record)


@router.put("/{content_id}", response_model=ContentRecord)
def update_content_record_by_id(content_id: int, payload: ContentCreate, db: Session = Depends(get_db)):
    record = update_content_record(db, content_id, payload.title, payload.content, payload.description)
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return record


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
        content=payload.content,
        description=payload.description,
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
    )


@router.post("/{content_id}/categories", response_model=ContentCategoryAssignment)
def assign_category(
    content_id: int,
    payload: ContentCategoryAssignmentCreate,
    db: Session = Depends(get_db),
):
    try:
        assignment = assign_category_to_content(
            db=db,
            content_id=content_id,
            category_id=payload.category_id,
            score=payload.score,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already assigned to this content record",
        )

    return ContentCategoryAssignment(
        id=assignment.id,
        content_id=assignment.content_id,
        category_id=assignment.category_id,
        score=assignment.score,
    )


@router.post("/versions", response_model=ContentVersion)
def create_version(
    payload: ContentVersionCreate,
    db: Session = Depends(get_db),
):
    version = create_content_version(
        db=db,
        content_record_id=payload.content_record_id,
        created_by=payload.created_by,
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return version


@router.get("/{content_record_id}/versions", response_model=list[ContentVersion])
def get_content_versions(
    content_record_id: int,
    db: Session = Depends(get_db),
):
    return list_versions_for_content(
        db=db,
        content_record_id=content_record_id,
    )


@router.post("/category-relations", response_model=CategoryRelation)
def create_category_relation_record(
    payload: CategoryRelationCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_category_relation(
            db=db,
            parent_category_id=payload.parent_category_id,
            child_category_id=payload.child_category_id,
            relation_type=payload.relation_type,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get(
    "/categories/{category_id}/parents",
    response_model=list[CategoryRelation],
)
def get_parent_relations_for_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    return list_parent_relations_for_category(
        db=db,
        child_category_id=category_id,
    )


@router.get(
    "/categories/{category_id}/children",
    response_model=list[CategoryRelation],
)
def get_child_relations_for_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    return list_child_relations_for_category(
        db=db,
        parent_category_id=category_id,
    )