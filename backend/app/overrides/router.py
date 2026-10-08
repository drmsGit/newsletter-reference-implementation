from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import request_principal, working_brand
from app.auth.service import actor_label
from app.pagination import Page, PageParams, page_params
from app.database import get_db
from app.overrides.models import (
    ContentOverride, ContentOverrideCreate, ModuleOverrideState, OutcomeDeltaUpdate, OverrideFieldsSet,
)
from app.audit import service as audit
# The version-token helpers the composer routes use (task-110), so an
# override write states and checks a module's version the same way.
from app.campaigns.router import IF_MATCH, _expected
from app.campaigns import fence
from app.campaigns.service import StaleWrite
from app.overrides.service import (
    override_audit_detail,
    create_content_override,
    get_content_override,
    list_content_overrides,
    record_outcome_delta,
    reset_content_override,
    set_override_fields,
)

router = APIRouter(prefix="/overrides", tags=["overrides"])


@router.post("/", response_model=ContentOverride)
def create(
    data: ContentOverrideCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    fence.guard(db, request, module_id=data.module_instance_id)
    try:
        created = create_content_override(
            db, data, brand_id=brand_id, author=actor_label(request_principal(request)))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    audit.record_from_request(
        request, db, audit.OVERRIDE_CREATED, subject_type="override", subject_id=created.id,
        detail=override_audit_detail(created),
    )
    fence.touch(db, request, module_id=data.module_instance_id)
    return created


@router.get("/", response_model=Page[ContentOverride])
def list_overrides(
    module_instance_id: int | None = None,
    send_instance_id: int | None = None,
    active: bool | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_content_overrides(
        db,
        module_instance_id=module_instance_id,
        send_instance_id=send_instance_id,
        active=active,
        brand_id=brand_id,
        params=params,
    )


@router.get("/{override_id}", response_model=ContentOverride)
def get(override_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    override = get_content_override(db, override_id, brand_id=brand_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    return override


@router.post("/{override_id}/reset", response_model=ContentOverride)
def reset(override_id: int, request: Request, db: Session = Depends(get_db),
          brand_id: int = Depends(working_brand)):
    """Reset-to-original: deactivate the override, reverting the module to
    system-governed content. Keeps the row as history; who reset it is the
    audit entry's actor (task-252)."""
    fence.guard(db, request, override_id=override_id)
    override = reset_content_override(db, override_id, brand_id=brand_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    audit.record_from_request(
        request, db, audit.OVERRIDE_RESET, subject_type="override", subject_id=override_id,
        detail=override_audit_detail(override),
    )
    fence.touch(db, request, override_id=override_id)
    return override


@router.patch("/{override_id}/outcome", response_model=ContentOverride)
def update_outcome(override_id: int, data: OutcomeDeltaUpdate, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    override = record_outcome_delta(db, override_id, data, brand_id=brand_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    return override


#: The audit action for each thing a field-set write can do (task-256).
_SET_ACTIONS = {
    "created": audit.OVERRIDE_CREATED,
    "changed": audit.OVERRIDE_CHANGED,
    "reset": audit.OVERRIDE_RESET,
}


@router.put(
    "/modules/{module_id}",
    response_model=ModuleOverrideState,
    summary="Set a module's overridden fields, all at once",
    description=(
        "The whole set of overridden fields for one module: an override is "
        "created, changed in place, or reset (an empty set). Overriding one more "
        "field, or resetting one, is this set with that key added or removed "
        "(ADR-178 point 6). If-Match takes the module's updated_at, which every "
        "override write moves."
    ),
)
def set_fields(
    module_id: int,
    data: OverrideFieldsSet,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
    if_match: str | None = IF_MATCH,
):
    fence.guard(db, request, module_id=module_id)
    try:
        result = set_override_fields(
            db, module_id, data.field_overrides, data.reason,
            brand_id=brand_id, author=actor_label(request_principal(request)),
            expected_updated_at=_expected(if_match),
        )
    except StaleWrite as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404, detail="Module not found")
    module, live, happened, row = result
    if happened is not None:
        audit.record_from_request(
            request, db, _SET_ACTIONS[happened], subject_type="override", subject_id=row.id,
            detail=override_audit_detail(row),
        )
    fence.touch(db, request, module_id=module_id)
    return {"module_id": module.id, "module_updated_at": module.updated_at, "override": live}
