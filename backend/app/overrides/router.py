from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.overrides.models import ContentOverride, ContentOverrideCreate, OutcomeDeltaUpdate
from app.overrides.service import (
    create_content_override,
    get_content_override,
    list_content_overrides,
    record_outcome_delta,
    reset_content_override,
)

router = APIRouter(prefix="/overrides", tags=["overrides"])


@router.post("/", response_model=ContentOverride)
def create(data: ContentOverrideCreate, db: Session = Depends(get_db)):
    try:
        return create_content_override(db, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/", response_model=list[ContentOverride])
def list_overrides(
    module_instance_id: int | None = None,
    send_instance_id: int | None = None,
    active: bool | None = None,
    db: Session = Depends(get_db),
):
    return list_content_overrides(
        db,
        module_instance_id=module_instance_id,
        send_instance_id=send_instance_id,
        active=active,
    )


@router.get("/{override_id}", response_model=ContentOverride)
def get(override_id: int, db: Session = Depends(get_db)):
    override = get_content_override(db, override_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    return override


@router.post("/{override_id}/reset", response_model=ContentOverride)
def reset(override_id: int, db: Session = Depends(get_db)):
    """Reset-to-original: deactivate the override, reverting the module to
    system-governed content. Keeps the row as history."""
    override = reset_content_override(db, override_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    return override


@router.patch("/{override_id}/outcome", response_model=ContentOverride)
def update_outcome(override_id: int, data: OutcomeDeltaUpdate, db: Session = Depends(get_db)):
    override = record_outcome_delta(db, override_id, data)
    if override is None:
        raise HTTPException(status_code=404, detail="Content override not found")
    return override
