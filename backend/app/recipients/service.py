from sqlalchemy.orm import Session

from app.recipients.db_models import RecipientDB
from app.recipients.models import Recipient


def to_recipient(record: RecipientDB) -> Recipient:
    return Recipient(
        id=record.id,
        external_id=record.external_id,
        email=record.email,
        language=record.language,
        preferred_airport=record.preferred_airport,
        attributes=record.attributes,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def create_recipient(
    db: Session,
    external_id: str,
    email: str,
    language: str | None = None,
    preferred_airport: str | None = None,
    attributes: dict | None = None,
    status: str = "active",
) -> Recipient:
    recipient = RecipientDB(
        external_id=external_id,
        email=email,
        language=language,
        preferred_airport=preferred_airport,
        attributes=attributes,
        status=status,
    )

    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    return to_recipient(recipient)


def list_recipients(db: Session) -> list[Recipient]:
    records = db.query(RecipientDB).order_by(RecipientDB.id.asc()).all()
    return [to_recipient(record) for record in records]


def get_recipient_by_external_id(
    db: Session,
    external_id: str,
) -> Recipient | None:
    record = (
        db.query(RecipientDB)
        .filter(RecipientDB.external_id == external_id)
        .first()
    )

    if record is None:
        return None

    return to_recipient(record)