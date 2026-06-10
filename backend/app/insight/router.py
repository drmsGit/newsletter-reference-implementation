from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.insight.models import EngagementEvent, EngagementEventCreate
from app.insight.service import (
    create_engagement_event,
    list_events_for_delivery_execution,
)


router = APIRouter(prefix="/insight", tags=["insight"])


@router.post("/events", response_model=EngagementEvent)
def create_event(
    payload: EngagementEventCreate,
    db: Session = Depends(get_db),
):
    return create_engagement_event(
        db=db,
        delivery_execution_id=payload.delivery_execution_id,
        event_type=payload.event_type,
        provider=payload.provider,
        provider_event_id=payload.provider_event_id,
        event_data=payload.event_data,
        occurred_at=payload.occurred_at,
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