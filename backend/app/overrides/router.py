from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.overrides.models import OverrideEvent, OverrideEventCreate, OutcomeDeltaUpdate
from app.overrides.service import (
    create_override_event,
    get_override_event,
    list_override_events,
    record_outcome_delta,
)

router = APIRouter(prefix="/overrides", tags=["overrides"])


@router.post("/", response_model=OverrideEvent)
def create(data: OverrideEventCreate, db: Session = Depends(get_db)):
    try:
        return create_override_event(db, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/", response_model=list[OverrideEvent])
def list_events(
    module_instance_id: int | None = None,
    send_instance_id: int | None = None,
    db: Session = Depends(get_db),
):
    return list_override_events(db, module_instance_id=module_instance_id, send_instance_id=send_instance_id)


@router.get("/{override_id}", response_model=OverrideEvent)
def get(override_id: int, db: Session = Depends(get_db)):
    event = get_override_event(db, override_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Override event not found")
    return event


@router.patch("/{override_id}/outcome", response_model=OverrideEvent)
def update_outcome(override_id: int, data: OutcomeDeltaUpdate, db: Session = Depends(get_db)):
    event = record_outcome_delta(db, override_id, data)
    if event is None:
        raise HTTPException(status_code=404, detail="Override event not found")
    return event
