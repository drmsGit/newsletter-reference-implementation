from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.recipients.models import Recipient, RecipientCreate
from app.recipients.service import (
    create_recipient,
    get_recipient_by_external_id,
    list_recipients,
)


router = APIRouter(prefix="/recipients", tags=["recipients"])


@router.post("/", response_model=Recipient)
def create_recipient_record(
    payload: RecipientCreate,
    db: Session = Depends(get_db),
):
    return create_recipient(
        db=db,
        external_id=payload.external_id,
        email=payload.email,
        language=payload.language,
        preferred_airport=payload.preferred_airport,
        attributes=payload.attributes,
        status=payload.status,
    )


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