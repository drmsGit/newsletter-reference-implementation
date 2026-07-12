from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.providers.models import ProviderEventCreate, ProviderEventIngestResult, ProviderEventQuarantine
from app.providers.service import ingest_provider_event, list_quarantined_events

router = APIRouter(
    prefix="/provider",
    tags=["provider"],
)


@router.post(
    "/events",
    response_model=ProviderEventIngestResult,
)
def create_provider_event(
    payload: ProviderEventCreate,
    db: Session = Depends(get_db),
):
    return ingest_provider_event(
        db=db,
        provider=payload.provider,
        provider_message_id=payload.provider_message_id,
        event_type=payload.event_type,
        provider_event_id=payload.provider_event_id,
        event_data=payload.event_data,
    )


@router.get(
    "/quarantine",
    response_model=list[ProviderEventQuarantine],
)
def get_quarantined_events(db: Session = Depends(get_db)):
    return list_quarantined_events(db)