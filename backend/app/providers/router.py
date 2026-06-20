from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.providers.models import ProviderEventCreate
from app.providers.service import ingest_provider_event
from app.insight.models import EngagementEvent

router = APIRouter(
    prefix="/provider",
    tags=["provider"],
)


@router.post(
    "/events",
    response_model=EngagementEvent,
)
def create_provider_event(
    payload: ProviderEventCreate,
    db: Session = Depends(get_db),
):
    try:
        return ingest_provider_event(
            db=db,
            provider=payload.provider,
            provider_message_id=payload.provider_message_id,
            event_type=payload.event_type,
            provider_event_id=payload.provider_event_id,
            event_data=payload.event_data,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )