from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.auth.permissions import CONTENT_MANAGE
from app.auth.dependencies import auth_is_enforced, request_principal, working_brand
from app.campaigns import duplication
# The version-token helpers the composer routes use (task-110), so a catalogue
# edit states and checks its version the same way (task-257).
from app.campaigns.router import IF_MATCH, _expected
from app.campaigns.service import StaleWrite
from app.auth.service import actor_label
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db
from app.content.db_models import CategoryDB
from app.content.models import (
    ContentDraft,
    ContentDraftRequest,
    ContentDraftStarted,
    ContentField,
    ContentListItem,
    ContentRecord,
    ContentRecordDetail,
    ContentReach,
    ContentCreate,
    ContentDuplicate,
    ContentDuplicateTarget,
    ContentAssignment,
    ContentPerformance,
    ContentUsage,
    ContentCampaign,
    Category,
    CategoryChange,
    CategoryCreate,
    CategoryRelation,
    CategoryRelationCreate,
    ContentCategoryAssignment,
    ContentCategoryAssignmentCreate,
    ContentCategoryAssignmentScore,
    ChannelReadiness,
    MachineReady,
    ContentVersion,
    ContentVersionCreate,
    ContentStatusUpdate,
    ContentPatch,
)
from app.content.service import (
    ContentImageInvalid,
    catalogue_fields,
    merge_content_fields,
    get_content_record,
    publish_state,
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


@router.get("/", response_model=Page[ContentListItem])
def get_content_records(
    q: str | None = Query(None, description="Find by title or description (part, any case)."),
    status: Literal["active", "inactive"] | None = Query(None, description="Only records in this status."),
    category_id: int | None = Query(
        None,
        description="Only records assigned to this category directly (not its children), "
        "ordered by their score in it, highest first.",
    ),
    ready_for: str | None = Query(
        None, description="Only records a person marked ready for this channel (ADR-174)."),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """One ADR-185 page of the brand's content records, newest first unless a
    category orders them (ADR-175 addendum 2026-10-04). Each row says which
    channels it is ready for (task-283)."""
    from app.content.service import page_content_records

    return page_content_records(
        db, params, brand_id=brand_id, q=q, status=status, category_id=category_id,
        ready_for=ready_for,
    )


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
    request: Request,
    force: bool = False,
    db: Session = Depends(get_db),
):
    category = db.get(CategoryDB, category_id)
    try:
        deleted = delete_category(db, category_id, force=force)
    except HasRelationsError as error:
        raise HTTPException(status_code=409, detail={"message": str(error), "counts": error.counts})
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    _category_audit(request, db, audit.CATEGORY_DELETED, category_id,
                    {"name": category.name if category else None, "forced": force})
    return {"status": "deleted"}


def _category_audit(request, db, action: str, category_id: int, detail: dict) -> None:
    """The shared taxonomy's writes (task-359), on the working brand's log."""
    audit.record_from_request(request, db, action, subject_type="category", subject_id=category_id, detail=detail)


@router.patch("/categories/{category_id}", response_model=Category,
              summary="Rename a category or change its type",
              description="Categories are shared by every brand (ADR-150): the change reaches all of them.")
def change_category_record(category_id: int, payload: CategoryChange, request: Request,
                           db: Session = Depends(get_db)):
    from app.content.service import change_category

    try:
        result = change_category(db, category_id, name=payload.name, type=payload.type)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404, detail="Category not found")
    category, changed = result
    if changed:
        _category_audit(request, db, audit.CATEGORY_CHANGED, category_id, changed)
    return category


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


@router.get("/{content_id}", response_model=ContentRecordDetail)
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
    from app.content.service import readiness_of

    latest, unpublished = publish_state(db, record)
    return {**to_content_record(record).model_dump(),
            "latest_version_number": latest, "unpublished_changes": unpublished,
            "machine_ready": bool(record.machine_ready), "readiness": readiness_of(db, record)}


def _record_edit(request, db, record, before: dict, run_id: int | None = None) -> None:
    """The audit entry for a catalogue edit (task-257, ADR-153 point 4): which
    record, and which fields the edit changed — not every key sent (task-275,
    `content.service.edited_fields`) — and the AI draft it came from, if any."""
    from app.content.service import edited_fields

    audit.record_from_request(
        request, db, audit.CONTENT_UPDATED, subject_type="content", subject_id=record.id,
        detail={"title": record.title, "fields": edited_fields(before, record),
                **_from_draft(db, run_id, record.id)},
    )


def _from_draft(db: Session, run_id: int | None, content_id: int) -> dict:
    """Names the AI draft run a person took this from (task-368), only when it
    is this record's draft run."""
    from app.ai.service import applied_run
    from app.ai.tasks.content_draft import TASK_KEY

    return applied_run(db, run_id, task_key=TASK_KEY, target_type="content", target_id=content_id)


def _record_content_write(request, db, action: str, content_id: int, detail: dict) -> None:
    """Every other content write, audited the same way on both planes (task-275)."""
    audit.record_from_request(
        request, db, action, subject_type="content", subject_id=content_id, detail=detail,
    )


@router.put("/{content_id}", response_model=ContentRecord)
def update_content_record_by_id(
    content_id: int,
    payload: ContentCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
    if_match: str | None = IF_MATCH,
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
    from app.content.service import edit_snapshot

    existing = get_content_record(db, content_id, brand_id=brand_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    before = edit_snapshot(existing)
    try:
        record = update_content_record(
            db, content_id, payload.title, payload.content, payload.description,
            brand_id=brand_id, expected_updated_at=_expected(if_match),
        )
    except StaleWrite as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ContentImageInvalid as error:
        raise HTTPException(status_code=422, detail=str(error))
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    _record_edit(request, db, record, before)
    return record


@router.patch("/{content_id}", response_model=ContentRecord)
def patch_content_record(
    content_id: int,
    payload: ContentPatch,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
    if_match: str | None = IF_MATCH,
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
    from app.content.service import edit_snapshot

    existing = get_content_record(db, content_id, brand_id=brand_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    before = edit_snapshot(existing)
    try:
        merged = merge_content_fields(
            existing.content, payload.content, groups=payload.groups,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    try:
        record = update_content_record(
            db, content_id,
            payload.title if payload.title is not None else existing.title,
            merged,
            payload.description if payload.description is not None else existing.description,
            brand_id=brand_id,
            # Checked against the row as it is now, so the merge above — made
            # from `existing` — is only written when it was made from current data.
            expected_updated_at=_expected(if_match),
        )
    except StaleWrite as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ContentImageInvalid as error:
        raise HTTPException(status_code=422, detail=str(error))
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    _record_edit(request, db, record, before, payload.applied_suggestion_run_id)
    return record


@router.put("/{content_id}/status", response_model=ContentRecord)
def set_content_record_status(
    content_id: int,
    payload: ContentStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Activate/deactivate a content record — the safe alternative to deleting."""
    existing = get_content_record(db, content_id, brand_id=brand_id)
    previous = existing.status if existing is not None else None
    try:
        record = set_content_status(db, content_id, payload.status, brand_id=brand_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    if previous != record.status:
        _record_content_write(request, db, audit.CONTENT_STATUS_CHANGED, content_id,
                              {"title": record.title, "from": previous, "to": record.status})
    return record


@router.delete("/{content_id}")
def delete_content_record_by_id(
    content_id: int,
    request: Request,
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
    _record_content_write(request, db, audit.CONTENT_DELETED, content_id, {**deleted, "forced": force})
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
    request: Request,
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
    try:
        record = create_content(
            db=db,
            title=payload.title,
            content=payload.content,
            brand_id=brand_id,
            description=payload.description,
        )
    except ContentImageInvalid as error:
        raise HTTPException(status_code=422, detail=str(error))
    _record_content_write(request, db, audit.CONTENT_CREATED, record.id,
                          {"title": record.title, "fields": sorted(record.content or {})})
    return record

@router.post("/categories", response_model=Category)
def create_category_record(
    payload: CategoryCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        category = create_category(db=db, name=payload.name, type=payload.type)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    _category_audit(request, db, audit.CATEGORY_CREATED, category.id, {"name": category.name, "type": category.type})
    return category


@router.post("/{content_id}/categories", response_model=ContentCategoryAssignment)
def assign_category(
    content_id: int,
    payload: ContentCategoryAssignmentCreate,
    request: Request,
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
    from app.content.service import assignment_summary

    _record_content_write(request, db, audit.CONTENT_CATEGORY_ASSIGNED, content_id,
                          {**assignment_summary(db, assignment),
                           **_from_draft(db, payload.applied_suggestion_run_id, content_id)})

    return ContentCategoryAssignment(
        id=assignment.id,
        content_id=assignment.content_id,
        category_id=assignment.category_id,
        score=assignment.score,
    )


@router.post("/versions", response_model=ContentVersion)
def create_version(
    payload: ContentVersionCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    version = create_content_version(
        db=db,
        content_record_id=payload.content_record_id,
        # Who published is the caller, never a field of the body (task-243's
        # rule; this route took `created_by` from the body until 2026-10-03).
        created_by=actor_label(request_principal(request)),
        brand_id=brand_id,
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    audit.record_from_request(
        request, db, audit.CONTENT_PUBLISHED, subject_type="content",
        subject_id=payload.content_record_id, detail={"version_number": version.version_number},
    )
    return version


@router.get("/{content_record_id}/versions", response_model=list[ContentVersion])
def get_content_versions(
    content_record_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    # 404 like every other content route (task-277, ADR-172 point 6). The list
    # was already brand-scoped, but it answered `[]` for a record that is not
    # the brand's or not there, which reads the same as "no versions yet".
    if get_content_record(db, content_record_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return list_versions_for_content(
        db=db,
        content_record_id=content_record_id,
        brand_id=brand_id,
    )


@router.post("/category-relations", response_model=CategoryRelation)
def create_category_relation_record(
    payload: CategoryRelationCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        relation = create_category_relation(
            db=db,
            parent_category_id=payload.parent_category_id,
            child_category_id=payload.child_category_id,
            relation_type=payload.relation_type,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    _category_audit(request, db, audit.CATEGORY_RELATION_ADDED, payload.child_category_id,
                    {"parent_category_id": payload.parent_category_id, "relation_id": relation.id})
    return relation


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


@router.post(
    "/{content_id}/drafts",
    response_model=ContentDraftStarted,
    summary="Ask the model to draft this record's text fields and propose its categories",
    description=(
        "task-368 (ADR-141 addendum 2026-10-16). Nothing is written to the record: the "
        "proposal is read back from `GET /content/{id}/drafts` and a person takes what "
        "they want through the ordinary writes. The source is sent to the model and never "
        "stored. Refused on the field at fault (422), before anything is spent, for an "
        "empty or over-long source or channels with no text fields."
    ),
)
def draft_content_record(
    content_id: int, payload: ContentDraftRequest, request: Request,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.ai.tasks import content_draft
    from app.auth.db_models import IntegrationDB

    if get_content_record(db, content_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    try:
        content_draft.check_request(payload.source, payload.channels)
    except content_draft.DraftInvalid as error:
        # The shape FastAPI gives a validation error, so a client shows it on the field.
        raise HTTPException(status_code=422, detail=[{"loc": ["body", error.field], "msg": str(error),
                                                      "type": "value_error"}])
    principal = request_principal(request)
    actor = ("integration" if isinstance(principal, IntegrationDB) else "user") if principal else None
    run = content_draft.draft(db, content_id, payload.source, payload.channels,
                              actor_type=actor, actor_id=principal.id if principal else None)
    return ContentDraftStarted(ai_run_id=run.run_id, status="ok" if run.ok else "refused", message=run.message)


@router.get(
    "/{content_id}/drafts",
    response_model=list[ContentDraft],
    summary="Every AI draft of this record, newest first",
    description="With the record's current text and scores beside each proposal (task-368).",
)
def get_content_drafts(content_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    from app.ai.tasks.content_draft import drafts_for_record

    record = get_content_record(db, content_id, brand_id=brand_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    return drafts_for_record(db, record, brand_id=brand_id)


def _is_integration(request: Request) -> bool:
    from app.auth.db_models import IntegrationDB

    return isinstance(request_principal(request), IntegrationDB)


@router.put(
    "/{content_id}/readiness/{channel}",
    response_model=ChannelReadiness,
    summary="Mark the record ready for a channel",
    description=(
        "A person's mark takes effect at once (ADR-174 point 4). An integration's mark "
        "is held for a person in the approval inbox: 202 with the held request, one per "
        "record and channel, no deadline; approving marks it in the approver's name "
        "(task-206). Marking again keeps the first mark's who and when."
    ),
)
def mark_record_ready(
    content_id: int, channel: str, request: Request,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import mark_ready, readiness_warning

    if _is_integration(request):
        # Unreachable through the guard, which holds every integration's mark
        # for a person (task-206, `HELD_FOR_EVERY_INTEGRATION`). Kept so that a
        # mapping lost from the policy refuses rather than marks unheld.
        raise HTTPException(
            status_code=403,
            detail="An integration's readiness mark must be approved by a person.",
        )
    try:
        marked = mark_ready(db, content_id, channel, marked_by=actor_label(request_principal(request)),
                            brand_id=brand_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    if marked is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    row, created = marked
    if created:
        _record_content_write(request, db, audit.CONTENT_READY_MARKED, content_id, {"channel": channel})
    record = get_content_record(db, content_id, brand_id=brand_id)
    return ChannelReadiness(channel=row.channel, marked_by=row.marked_by, marked_at=row.marked_at,
                            warning=readiness_warning(record.content, channel))


@router.delete(
    "/{content_id}/readiness/{channel}",
    status_code=204,
    summary="Remove the record's mark for a channel",
    description=(
        "The safe direction, so a person or an integration may remove a mark directly "
        "(ADR-174 addendum 2026-10-05, point 5). Removing a mark that is not there is "
        "not an error."
    ),
)
def unmark_record_ready(
    content_id: int, channel: str, request: Request,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import unmark_ready

    if get_content_record(db, content_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    try:
        was = unmark_ready(db, content_id, channel, brand_id=brand_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    if was is not None:
        _record_content_write(request, db, audit.CONTENT_READY_UNMARKED, content_id, was)


@router.put(
    "/{content_id}/machine-ready",
    response_model=MachineReady,
    summary="Turn machine ready on or off",
    description=(
        "May a machine pick this record without a person deciding? People only: an "
        "integration is refused, because the flag is the human gate on what machines "
        "may pick (ADR-179 addendum 2026-10-05)."
    ),
)
def set_record_machine_ready(
    content_id: int, payload: MachineReady, request: Request,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import set_machine_ready

    if _is_integration(request):
        raise HTTPException(status_code=403, detail="Only a person may change machine ready.")
    changed = set_machine_ready(db, content_id, payload.machine_ready, brand_id=brand_id)
    if changed is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    record, previous = changed
    if previous != record.machine_ready:
        _record_content_write(request, db, audit.CONTENT_MACHINE_READY_CHANGED, content_id,
                              {"title": record.title, "from": previous, "to": record.machine_ready})
    return MachineReady(machine_ready=record.machine_ready)


@router.patch(
    "/{content_id}/assignments/{assignment_id}",
    response_model=ContentCategoryAssignment,
    summary="Change one assignment's score in place",
    description=(
        "1 to 10 (ADR-080's 2026-10-04 addendum). Through the record, within the "
        "working brand: another record's or another brand's assignment is not found. "
        "In place, so the record never drops out of the category mid-change."
    ),
)
def change_assignment_score(
    content_id: int, assignment_id: int, payload: ContentCategoryAssignmentScore, request: Request,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import set_assignment_score

    changed = set_assignment_score(db, content_id, assignment_id, payload.score, brand_id=brand_id)
    if changed is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    before, after = changed
    if before["score"] != after["score"]:
        _record_content_write(request, db, audit.CONTENT_CATEGORY_SCORE_CHANGED, content_id, {
            "category_id": after["category_id"], "category": after["category"],
            "from": before["score"], "to": after["score"],
            **_from_draft(db, payload.applied_suggestion_run_id, content_id),
        })
    return ContentCategoryAssignment(
        id=assignment_id, content_id=content_id,
        category_id=after["category_id"], score=after["score"],
    )


@router.delete(
    "/{content_id}/assignments/{assignment_id}",
    status_code=204,
    summary="Remove one category from the record",
    description="Through the record, within the working brand (task-241): another record's or another brand's assignment is not found.",
)
def delete_content_assignment(
    content_id: int, assignment_id: int, request: Request,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.service import delete_category_assignment

    removed = delete_category_assignment(db, content_id, assignment_id, brand_id=brand_id)
    if removed is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _record_content_write(request, db, audit.CONTENT_CATEGORY_UNASSIGNED, content_id, removed)


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


@router.get(
    "/{content_id}/performance",
    response_model=ContentPerformance,
    summary="How the record did: deliveries, clicks and its share of clicks, overall and per campaign",
    description="Counted per delivery, all time, on read (ADR-196 addendum 2026-10-16). The click "
                "share is its clicks over all clicks in the deliveries that carried it.",
)
def get_content_performance(
    content_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.content.kpis import content_figures
    from app.content.service import get_content_record

    if get_content_record(db, content_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    overall, per_campaign, names = content_figures(db, brand_id, [content_id], by_campaign=True)
    empty = {"deliveries": 0, "picked": 0, "clicks": 0, "unique_clickers": 0, "clicks_in_deliveries": 0,
             "click_share": None}
    campaigns = sorted((per_campaign.get(content_id) or {}).items(), key=lambda item: -item[1]["deliveries"])
    return {
        "overall": overall.get(content_id, empty),
        "by_campaign": [{"campaign_id": cid, "campaign_name": names.get(cid, f"Campaign {cid}"), "figures": f}
                        for cid, f in campaigns],
    }


@router.delete(
    "/category-relations/{relation_id}",
    status_code=204,
    summary="Remove a link between two categories",
    description="The taxonomy is shared by every brand (ADR-150), so this is not brand-scoped.",
)
def delete_category_relation_route(relation_id: int, request: Request, db: Session = Depends(get_db)):
    from app.content.db_models import CategoryRelationDB
    from app.content.service import delete_category_relation

    relation = db.get(CategoryRelationDB, relation_id)
    pair = (relation.parent_category_id, relation.child_category_id) if relation else None
    if not delete_category_relation(db, relation_id):
        raise HTTPException(status_code=404, detail="Category relation not found")
    _category_audit(request, db, audit.CATEGORY_RELATION_REMOVED, pair[1],
                    {"parent_category_id": pair[0], "relation_id": relation_id})


@router.get(
    "/{content_id}/campaigns",
    response_model=Page[ContentCampaign],
    summary="The campaigns whose modules use this record, sent ones included",
    description=(
        "Campaigns in the brand with a module bound to the record, each with the "
        "variants that use it and their stage; a sent variant's stage is \"sent\". "
        "A decision slot that may pick the record at send time is not listed."
    ),
)
def get_campaigns_using(
    content_id: int,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.campaigns.monitoring import campaigns_using

    if get_content_record(db, content_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    # Grows with use, so paged (ADR-185); built in Python from monitoring's
    # read model, like the monitoring list itself.
    return page_of_list(campaigns_using(db, content_id, brand_id=brand_id), params)


@router.get(
    "/{content_id}/unsent-campaigns",
    response_model=ContentReach,
    summary="The unsent campaigns an edit to this record would reach",
    description=(
        "Campaigns in the brand with a module bound to the record and a variant "
        "using it that has not been sent. Sent campaigns are snapshotted and "
        "immune, so they are left out (ADR-178 point 8)."
    ),
)
def get_unsent_campaigns(
    content_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.campaigns.monitoring import unsent_campaigns_using

    if get_content_record(db, content_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Content record not found")
    campaigns = unsent_campaigns_using(db, content_id, brand_id=brand_id)
    return {"count": len(campaigns), "campaigns": campaigns}
