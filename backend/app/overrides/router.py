from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import request_principal, working_brand
from app.auth.service import actor_label
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db
from app.overrides.models import ContentOverride, ContentOverrideCreate, OutcomeDeltaUpdate
from app.audit import service as audit
from app.overrides.service import (
    override_audit_detail,
    create_content_override,
    get_content_override,
    list_content_overrides,
    record_outcome_delta,
    reset_content_override,
)

router = APIRouter(prefix="/overrides", tags=["overrides"])


@router.post("/", response_model=ContentOverride)
def create(
    data: ContentOverrideCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        created = create_content_override(
            db, data, brand_id=brand_id, author=actor_label(request_principal(request)))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    audit.record_from_request(
        request, db, audit.OVERRIDE_CREATED, subject_type="override", subject_id=created.id,
        detail=override_audit_detail(created),
    )
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
    override = reset_content_override(db, override_id, brand_id=brand_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    audit.record_from_request(
        request, db, audit.OVERRIDE_RESET, subject_type="override", subject_id=override_id,
        detail=override_audit_detail(override),
    )
    return override


@router.patch("/{override_id}/outcome", response_model=ContentOverride)
def update_outcome(override_id: int, data: OutcomeDeltaUpdate, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    override = record_outcome_delta(db, override_id, data, brand_id=brand_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    return override
