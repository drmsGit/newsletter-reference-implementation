from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.recipients.models import (
    ConsentDriftItem,
    ConsentSyncLog,
    ConsentSyncRequest,
    Recipient,
    RecipientCreate,
    RecipientPreference,
    RecipientPreferenceCreate,
)
from app.recipients.service import (
    create_recipient,
    detect_consent_drift,
    get_recipient_by_external_id,
    list_consent_sync_logs,
    list_recipients,
    create_recipient_preference,
    list_preferences_for_recipient,
    sync_consent_from_crm,
)


router = APIRouter(prefix="/recipients", tags=["recipients"])


@router.post("/", response_model=Recipient)
def create_recipient_record(
    payload: RecipientCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_recipient(
            db=db,
            external_id=payload.external_id,
            email=payload.email,
            language=payload.language,
            attributes=payload.attributes,
            status=payload.status,
            consent_status=payload.consent_status.value,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/", response_model=list[Recipient])
def get_recipients(db: Session = Depends(get_db)):
    return list_recipients(db)


# --- Consent (CRM-synced) -------------------------------------------------
# Registered before the "/{external_id}" catch-all so these fixed multi-segment
# paths resolve correctly. GET drift/sync-log are 2-segment, so they can't be
# swallowed by the single-segment "/{external_id}" route regardless of order.


@router.get("/consent/drift", response_model=list[ConsentDriftItem])
def get_consent_drift(db: Session = Depends(get_db)):
    """Recipients whose platform consent_status diverges from the CRM's most
    recent assertion — a sync that failed to stick, which must not be silent."""
    return detect_consent_drift(db)


@router.get("/consent/sync-log", response_model=list[ConsentSyncLog])
def get_consent_sync_log(
    recipient_id: int | None = None,
    db: Session = Depends(get_db),
):
    return list_consent_sync_logs(db, recipient_id=recipient_id)


@router.post("/{external_id}/consent", response_model=Recipient)
def sync_recipient_consent(
    external_id: str,
    payload: ConsentSyncRequest,
    db: Session = Depends(get_db),
):
    """Apply a CRM consent assertion to the local projection and log it."""
    try:
        return sync_consent_from_crm(
            db=db,
            external_id=external_id,
            crm_consent_status=payload.consent_status.value,
            source=payload.source,
            note=payload.note,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/{external_id}", response_model=Recipient)
def get_recipient(
    external_id: str,
    db: Session = Depends(get_db),
):
    recipient = get_recipient_by_external_id(
        db=db,
        external_id=external_id,
    )

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail="Recipient not found",
        )

    return recipient


@router.get(
    "/{recipient_id}/preferences",
    response_model=list[RecipientPreference],
)
def get_preferences(
    recipient_id: int,
    db: Session = Depends(get_db),
):
    return list_preferences_for_recipient(
        db=db,
        recipient_id=recipient_id,
    )


@router.post(
    "/preferences",
    response_model=RecipientPreference,
)
def create_preference(
    payload: RecipientPreferenceCreate,
    db: Session = Depends(get_db),
):
    return create_recipient_preference(
        db=db,
        recipient_id=payload.recipient_id,
        category_id=payload.category_id,
        score=payload.score,
        source=payload.source,
    )