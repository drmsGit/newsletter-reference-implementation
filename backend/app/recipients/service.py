from sqlalchemy.orm import Session

from app.recipients.db_models import RecipientDB, RecipientPreferenceDB
from app.recipients.models import Recipient, RecipientPreference

# RecipientDB.attributes is an open bag for engagement/personalization-relevant
# data (e.g. firstname, preferred_airport, loyalty_tier) — it is allowed to
# grow richer over time (including via AI/decisioning-driven enrichment), but
# must never become a CRM-owned data store (ADR-126: the Recipient Projection
# "must not become... a full customer profile repository... a system of
# record for customer data"). Rather than enumerate every allowed key (the
# allowed set is intentionally open-ended), reject the common CRM-only field
# shapes by name.
_FORBIDDEN_ATTRIBUTE_KEY_PATTERNS = (
    "address",
    "invoice",
    "ssn",
    "social_security",
    "payment",
    "billing",
    "phone",
    "service_case",
    "ticket",
    "passport",
    "credit_card",
    "iban",
    "bank_account",
    "tax_id",
)


def validate_recipient_attributes(attributes: dict | None) -> None:
    if not attributes:
        return

    for key in attributes:
        normalized = key.lower()
        for forbidden in _FORBIDDEN_ATTRIBUTE_KEY_PATTERNS:
            if forbidden in normalized:
                raise ValueError(
                    f"attributes key '{key}' looks like CRM-owned data (matches "
                    f"forbidden pattern '{forbidden}') — the Recipient Projection "
                    "must not become a customer profile repository (ADR-126). "
                    "Keep this data in the CRM."
                )


def to_recipient(record: RecipientDB) -> Recipient:
    return Recipient(
        id=record.id,
        external_id=record.external_id,
        email=record.email,
        language=record.language,
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
    attributes: dict | None = None,
    status: str = "active",
) -> Recipient:
    validate_recipient_attributes(attributes)

    recipient = RecipientDB(
        external_id=external_id,
        email=email,
        language=language,
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


def to_recipient_preference(
    record: RecipientPreferenceDB,
) -> RecipientPreference:

    return RecipientPreference(
        id=record.id,
        recipient_id=record.recipient_id,
        category_id=record.category_id,
        score=record.score,
        source=record.source,
        created_at=record.created_at,
    )


def create_recipient_preference(
    db: Session,
    recipient_id: int,
    category_id: int,
    score: float,
    source: str = "manual",
):
    preference = RecipientPreferenceDB(
        recipient_id=recipient_id,
        category_id=category_id,
        score=score,
        source=source,
    )

    db.add(preference)
    db.commit()
    db.refresh(preference)

    return to_recipient_preference(
        preference
    )


def list_preferences_for_recipient(
    db: Session,
    recipient_id: int,
):
    records = (
        db.query(
            RecipientPreferenceDB
        )
        .filter(
            RecipientPreferenceDB.recipient_id
            == recipient_id
        )
        .order_by(
            RecipientPreferenceDB.score.desc()
        )
        .all()
    )

    return [
        to_recipient_preference(r)
        for r in records
    ]