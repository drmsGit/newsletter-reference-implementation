from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.recipients.models import Recipient, RecipientCreate, RecipientPreference, RecipientPreferenceCreate
from app.recipients.service import (
    create_recipient,
    get_recipient_by_external_id,
    list_recipients,
    create_recipient_preference,
    list_preferences_for_recipient,
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
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/", response_model=list[Recipient])
def get_recipients(db: Session = Depends(get_db)):
    return list_recipients(db)


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