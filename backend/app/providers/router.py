import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.providers.adapters.resend import parse_webhook, verify_signature
from app.providers.models import ProviderEventCreate, ProviderEventIngestResult, ProviderEventQuarantine
from app.providers.service import ingest_provider_event, list_quarantined_events, process_provider_webhook_event

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


@router.post("/webhooks/resend")
async def resend_webhook(request: Request, db: Session = Depends(get_db)):
    """Public webhook Resend POSTs engagement events to (opens/clicks/bounces).
    Full URL: POST /provider/webhooks/resend. Verifies the Svix signature, maps
    the raw payload to the canonical event via the Resend adapter, then records
    it + applies signals. Returns 200 for handled *and* ignored events so Resend
    doesn't retry an event we simply don't map; 401 only on a bad signature."""
    raw = await request.body()

    if not verify_signature(raw, dict(request.headers)):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    normalized = parse_webhook(payload)
    if normalized is None:
        return {"status": "ignored"}

    result = process_provider_webhook_event(db, normalized)
    return {"status": result.status}