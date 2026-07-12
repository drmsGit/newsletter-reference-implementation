from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.insight.models import EngagementEvent, EngagementEventCreate, PreferenceUpdateResult
from app.insight.service import (
    create_engagement_event,
    list_events_for_delivery_execution,
    apply_event_to_preferences,
)


router = APIRouter(prefix="/insight", tags=["insight"])


@router.post("/events", response_model=EngagementEvent)
def create_event(
    payload: EngagementEventCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_engagement_event(
            db=db,
            delivery_execution_id=payload.delivery_execution_id,
            event_type=payload.event_type,
            provider=payload.provider,
            provider_event_id=payload.provider_event_id,
            event_data=payload.event_data,
            occurred_at=payload.occurred_at,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Engagement event already recorded for provider={payload.provider!r}, provider_event_id={payload.provider_event_id!r}",
        )


@router.get("/delivery-executions/{delivery_execution_id}/events", response_model=list[EngagementEvent])
def get_events_for_delivery_execution(
    delivery_execution_id: int,
    db: Session = Depends(get_db),
):
    return list_events_for_delivery_execution(
        db=db,
        delivery_execution_id=delivery_execution_id,
    )


@router.post("/events/{event_id}/apply-preferences", response_model=PreferenceUpdateResult)
def apply_preferences_from_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    try:
        return apply_event_to_preferences(
            db=db,
            event_id=event_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )