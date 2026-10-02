from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.auth.permissions import CONTENT_MANAGE
from app.auth.dependencies import auth_is_enforced, request_principal, working_brand
from app.campaigns import duplication
from app.database import get_db
from app.content.models import (
    ContentField,
    ContentRecord,
    ContentCreate,
    ContentDuplicate,
    ContentDuplicateTarget,
    ContentAssignment,
    ContentUsage,
    Category,
    CategoryCreate,
    CategoryRelation,
    CategoryRelationCreate,
    ContentCategoryAssignment,
    ContentCategoryAssignmentCreate,
    ContentVersion,
    ContentVersionCreate,
    ContentStatusUpdate,
    ContentPatch,
)
from app.content.service import (
    catalogue_fields,
    merge_content_fields,
    list_content_records,
    get_content_record,
    to_content_record,
    update_content_record,
    set_content_status,
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
    delete_content_record,
    delete_category,
    ContentRecordHasHistoryError,
    HasRelationsError,
)



router = APIRouter(prefix="/content", tags=["content"])


@router.get("/", response_model=list[ContentRecord])
def get_content_records(
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_content_records(db, brand_id=brand_id)


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


# Same route-ordering requirement as the GETs above: this must be registered
# before DELETE /{content_id} or "categories" would be parsed as content_id.
@router.delete("/categories/{category_id}")
def delete_category_record(
    category_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
):
    try:
        deleted = delete_category(db, category_id, force=force)
    except HasRelationsError as error:
        raise HTTPException(status_code=409, detail={"message": str(error), "counts": error.counts})
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"status": "deleted"}


@router.get("/fields", response_model=list[ContentField])
def get_content_fields():
    """The fields a content record can carry, with what each one is.

    **Declared before `/{content_id}`, and that is not style.** FastAPI matches
    in declaration order, so after it this path would be read as a content id
    and answer 422.

    Derived rather than stored, which is the point of [[ADR-177]]: the client is
    given the answer instead of the manifests to work it out from. The client
    must not rebuild this — a second implementation of "which fields exist" in
    another language is how the two stop agreeing, which is the defect
    `CONTENT_FIELD_GROUPS` documented about its own duplicate for months.
    """
    return [ContentField(**field) for field in catalogue_fields()]


@router.get("/{content_id}", response_model=ContentRecord)
def get_content_record_by_id(
    content_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    # A record in another brand is not found, and answers exactly as a deleted
    # one does (ADR-172 point 6). A guessable integer id is not a secret.
    record = get_content_record(db, content_id, brand_id=brand_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return to_content_record(record)


@router.put("/{content_id}", response_model=ContentRecord)
def update_content_record_by_id(
    content_id: int,
    payload: ContentCreate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Replace a content record wholesale. **`content` is replaced, not merged.**

    That is what PUT means and it is left meaning it — but it is a loaded gun
    for a client that renders fields conditionally. A screen with push switched
    off sends no push keys, and this route will then remove them, which is
    exactly the data-loss bug the Jinja form was taught to avoid in 2026-09-17.

    **Use `PATCH` for a partial edit.** It takes the groups the caller was
    authoritative for and merges accordingly, which is the rule
    `content.service.merge_content_fields` holds for both planes.
    """
    record = update_content_record(
        db, content_id, payload.title, payload.content, payload.description,
        brand_id=brand_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return record


@router.patch("/{content_id}", response_model=ContentRecord)
def patch_content_record(
    content_id: int,
    payload: ContentPatch,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Edit a content record, merging onto what is stored.

    The rule, in one sentence: **a caller may only clear what it was
    offering.** `groups` says what that was; a key in a group the caller did
    not name is left exactly as found, and a key in no group at all is always
    preserved, because `content` is an open dict and a merge must not quietly
    become a schema.

    Added 2026-09-20. Until then this behaviour existed only inside
    `POST /ui/content/{id}/edit`, so the SPA had no way to edit a record
    without destroying the copy for whichever channel its screen was not
    showing.
    """
    existing = get_content_record(db, content_id, brand_id=brand_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    try:
        merged = merge_content_fields(
            existing.content, payload.content, groups=payload.groups,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    record = update_content_record(
        db, content_id,
        payload.title if payload.title is not None else existing.title,
        merged,
        payload.description if payload.description is not None else existing.description,
        brand_id=brand_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return record


@router.put("/{content_id}/status", response_model=ContentRecord)
def set_content_record_status(
    content_id: int,
    payload: ContentStatusUpdate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Activate/deactivate a content record — the safe alternative to deleting."""
    try:
        record = set_content_status(db, content_id, payload.status, brand_id=brand_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return record


@router.delete("/{content_id}")
def delete_content_record_by_id(
    content_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        deleted = delete_content_record(db, content_id, force=force, brand_id=brand_id)
    except ContentRecordHasHistoryError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except HasRelationsError as error:
        raise HTTPException(status_code=409, detail={"message": str(error), "counts": error.counts})
    if not deleted:
        raise HTTPException(status_code=404, detail="Content record not found")
    return {"status": "deleted"}


@router.get("/{content_id}/categories", response_model=list[Category])
def get_content_categories(
    content_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_categories_for_content(db, content_id, brand_id=brand_id)

@router.post("/", response_model=ContentRecord)
def create_content_record(
    payload: ContentCreate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    # The brand is the one the guard authorised (ADR-168, ADR-172 point 1):
    # `enforce_api_policy` resolves it — the declared `X-Brand` for a machine,
    # the session's working brand for a person — and `working_brand` hands it
    # here, so the row lands where the permission was checked. This route used
    # to check against the declared brand and write to the default one (task-39);
    # `test_brand_boundary.TestAPermittedWriteLandsOnTheDeclaredBrand` pins it.
    #
    # The "PROVISIONAL — this router is unauthenticated" note that opened here
    # is gone rather than amended, as in campaigns/router.py: it stopped being
    # true when launch gate 3 closed, and it was the half of task-39 most
    # likely to mislead — a reader told the routers are unguarded has a reason
    # to leave a brand bug alone.
    return create_content(
        db=db,
        title=payload.title,
        content=payload.content,
        brand_id=brand_id,
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
    brand_id: int = Depends(working_brand),
):
    # **Resolved here so the two refusals stay distinct.** The service answers
    # `None` for "already assigned", which the 409 below reports — and it also
    # refuses a record outside the brand. Letting both arrive as `None` would
    # tell a caller its assignment was a duplicate when the record simply is
    # not theirs, which is a worse answer than either.
    if get_content_record(db, content_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    try:
        assignment = assign_category_to_content(
            db=db,
            content_id=content_id,
            category_id=payload.category_id,
            score=payload.score,
            brand_id=brand_id,
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
    brand_id: int = Depends(working_brand),
):
    version = create_content_version(
        db=db,
        content_record_id=payload.content_record_id,
        created_by=payload.created_by,
        brand_id=brand_id,
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return version


@router.get("/{content_record_id}/versions", response_model=list[ContentVersion])
def get_content_versions(
    content_record_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_versions_for_content(
        db=db,
        content_record_id=content_record_id,
        brand_id=brand_id,
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

@router.get(
    "/{content_id}/duplicate-targets",
    response_model=list[ContentDuplicateTarget],
    summary="Brands this caller may copy this record into",
    description=(
        "The caller's own `content.manage` grants, brand by brand — the same rule "
        "`POST /content/{id}/duplicate` enforces, so every brand listed here is "
        "one that request would accept."
    ),
)
def duplicate_targets(
    content_id: int,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    if get_content_record(db, content_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail=f"ContentRecord {content_id} not found")
    return [
        ContentDuplicateTarget(id=b.id, name=b.name, crossing=b.id != brand_id)
        for b in duplication.target_brands(
            db, request_principal(request), permission=CONTENT_MANAGE,
            enforced=auth_is_enforced(request))
    ]


@router.post(
    "/{content_id}/duplicate",
    response_model=ContentRecord,
    status_code=201,
    summary="Copy one content record, possibly into another brand",
    description=(
        "One record, one step. The source must be in the working brand (404 "
        "otherwise). **`content.manage` is checked on the TARGET brand for the "
        "caller's own grants**; a brand that does not exist and one the caller "
        "holds no grant on both answer 403. The copy is a draft with no "
        "published version, so a campaign using it cannot send until someone "
        "publishes it."
    ),
)
def duplicate_content(
    content_id: int,
    payload: ContentDuplicate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    record = get_content_record(db, content_id, brand_id=brand_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"ContentRecord {content_id} not found")

    try:
        target = duplication.require_content_target(
            db,
            request_principal(request),
            target_brand_id=payload.target_brand_id,
            enforced=auth_is_enforced(request),
        )
    except duplication.DuplicationForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))

    try:
        copy = duplication.duplicate_content_record(
            db, content_id=record.id, target_brand_id=target.id
        )
    except duplication.DuplicationRefused as error:
        raise HTTPException(status_code=409, detail=str(error))

    audit.record_from_request(
        request, db, audit.CONTENT_DUPLICATED,
        subject_type="content_record", subject_id=copy.id, brand_id=target.id,
        detail={
            "source_content_id": record.id,
            "source_brand_id": record.brand_id,
            "target_brand_id": target.id,
        },
    )
    return to_content_record(copy)


@router.get(
    "/{content_id}/assignments",
    response_model=list[ContentAssignment],
    summary="The record's categories, with assignment id and score",
)
def get_content_assignments(
    content_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import content_assignments

    rows = content_assignments(db, content_id, brand_id=brand_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return rows


@router.delete(
    "/{content_id}/assignments/{assignment_id}",
    status_code=204,
    summary="Remove one category from the record",
    description="Through the record, within the working brand (task-241): another record's or another brand's assignment is not found.",
)
def delete_content_assignment(
    content_id: int, assignment_id: int,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import delete_category_assignment

    if not delete_category_assignment(db, content_id, assignment_id, brand_id=brand_id):
        raise HTTPException(status_code=404, detail="Assignment not found")


@router.get(
    "/{content_id}/usage",
    response_model=ContentUsage,
    summary="Where the record was picked, and the signals its engagement earned",
)
def get_content_usage(
    content_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import content_usage

    usage = content_usage(db, content_id, brand_id=brand_id)
    if usage is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return usage


@router.delete(
    "/category-relations/{relation_id}",
    status_code=204,
    summary="Remove a link between two categories",
    description="The taxonomy is shared by every brand (ADR-150), so this is not brand-scoped.",
)
def delete_category_relation_route(relation_id: int, db: Session = Depends(get_db)):
    from app.content.service import delete_category_relation

    if not delete_category_relation(db, relation_id):
        raise HTTPException(status_code=404, detail="Category relation not found")
