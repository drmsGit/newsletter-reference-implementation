from sqlalchemy.orm import Session

from app.recipients.db_models import ConsentSyncLogDB, RecipientDB
from app.recipients.models import (
    ConsentDriftItem,
    ConsentStatus,
    ConsentSyncLog,
    Recipient,
    RecipientPreference,
)

# The only consent value that clears the audience-resolution gate. "pending"
# and "opted_out" recipients are filtered out before decisioning/rendering.
CONSENTING_STATUS = ConsentStatus.opted_in.value

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
        consent_status=record.consent_status,
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
    consent_status: str = ConsentStatus.pending.value,
) -> Recipient:
    """Upserts keyed on external_id — a repeat CRM sync updates in place
    rather than hitting the unique constraint with a blind insert."""
    validate_recipient_attributes(attributes)

    recipient = (
        db.query(RecipientDB)
        .filter(RecipientDB.external_id == external_id)
        .first()
    )

    if recipient is None:
        recipient = RecipientDB(external_id=external_id)
        db.add(recipient)

    recipient.email = email
    recipient.language = language
    recipient.attributes = attributes
    recipient.status = status
    recipient.consent_status = consent_status

    db.commit()
    db.refresh(recipient)

    return to_recipient(recipient)


def sync_consent_from_crm(
    db: Session,
    external_id: str,
    crm_consent_status: str,
    source: str = "crm",
    note: str | None = None,
) -> Recipient:
    """Apply a CRM consent assertion to the local projection and record it in
    the append-only consent-sync log. The CRM is the source of truth; this
    keeps the platform's synced copy current and leaves an audit trail so a
    later divergence (a sync that silently failed to stick) is detectable via
    ``detect_consent_drift``."""
    recipient = (
        db.query(RecipientDB)
        .filter(RecipientDB.external_id == external_id)
        .first()
    )
    if recipient is None:
        raise ValueError(f"Recipient with external_id '{external_id}' not found")

    log = ConsentSyncLogDB(
        recipient_id=recipient.id,
        external_id=external_id,
        crm_consent_status=crm_consent_status,
        platform_status_before=recipient.consent_status,
        applied=True,
        source=source,
        note=note,
    )
    recipient.consent_status = crm_consent_status
    db.add(log)
    db.commit()
    db.refresh(recipient)

    return to_recipient(recipient)


def list_consent_sync_logs(
    db: Session,
    recipient_id: int | None = None,
) -> list[ConsentSyncLog]:
    q = db.query(ConsentSyncLogDB)
    if recipient_id is not None:
        q = q.filter(ConsentSyncLogDB.recipient_id == recipient_id)
    rows = q.order_by(ConsentSyncLogDB.synced_at.desc(), ConsentSyncLogDB.id.desc()).all()
    return [
        ConsentSyncLog(
            id=r.id,
            recipient_id=r.recipient_id,
            external_id=r.external_id,
            crm_consent_status=r.crm_consent_status,
            platform_status_before=r.platform_status_before,
            applied=r.applied,
            source=r.source,
            note=r.note,
            synced_at=r.synced_at,
        )
        for r in rows
    ]


def detect_consent_drift(db: Session) -> list[ConsentDriftItem]:
    """Surface recipients whose live consent_status disagrees with the most
    recent value the CRM asserted for them. In normal operation the two agree;
    a mismatch means a CRM assertion never took effect on the platform (the
    "CRM says no, platform still says yes" case that must not be silent)."""
    latest_logs: dict[int, ConsentSyncLogDB] = {}
    rows = (
        db.query(ConsentSyncLogDB)
        .order_by(ConsentSyncLogDB.synced_at.asc(), ConsentSyncLogDB.id.asc())
        .all()
    )
    # Walking oldest→newest leaves the newest entry per recipient in the map.
    for row in rows:
        latest_logs[row.recipient_id] = row

    drift: list[ConsentDriftItem] = []
    for recipient_id, log in latest_logs.items():
        recipient = (
            db.query(RecipientDB).filter(RecipientDB.id == recipient_id).first()
        )
        if recipient is None:
            continue
        if recipient.consent_status != log.crm_consent_status:
            drift.append(
                ConsentDriftItem(
                    recipient_id=recipient.id,
                    external_id=recipient.external_id,
                    email=recipient.email,
                    platform_consent_status=recipient.consent_status,
                    last_crm_consent_status=log.crm_consent_status,
                    last_synced_at=log.synced_at,
                )
            )
    return drift


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


def create_recipient_preference(
    db: Session,
    recipient_id: int,
    category_id: int,
    score: float,
    source: str = "manual",
):
    """A declared/manual preference is now a heavy, slowly-decaying *manual
    contribution* to the signal log (ADR-132) — there is no stored running
    total. `score` becomes the contribution's base weight, preserving the
    declared magnitude. Returns the recipient's current signal for the category."""
    from app.insight.signals import record_contribution, get_operational_signal

    record_contribution(
        db=db,
        recipient_id=recipient_id,
        category_id=category_id,
        contribution_type="manual",
        source=source,
        base_weight=score,
    )
    return RecipientPreference(
        recipient_id=recipient_id,
        category_id=category_id,
        score=get_operational_signal(db, recipient_id, category_id),
    )


def list_preferences_for_recipient(
    db: Session,
    recipient_id: int,
):
    """The recipient's current operational signal per category (decay-on-read),
    highest first — replaces the old stored preference rows."""
    from app.insight.signals import operational_signals_for_recipient

    signals = operational_signals_for_recipient(db, recipient_id)
    return [
        RecipientPreference(recipient_id=recipient_id, category_id=category_id, score=score)
        for category_id, score in sorted(signals.items(), key=lambda kv: kv[1], reverse=True)
    ]