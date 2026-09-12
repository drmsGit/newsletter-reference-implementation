from sqlalchemy.orm import Session

from app.recipients.consent import (
    CONSENTING_STATUS,
    DEFAULT_CHANNEL,
    DEFAULT_PURPOSE,
    latest_consent_event,
    latest_consent_status,
    record_consent,
)
from app.recipients.db_models import (
    AddressabilityDB,
    ConsentEventDB,
    ConsentSyncLogDB,
    RecipientDB,
)
from app.recipients.models import (
    ConsentDriftItem,
    ConsentStatus,
    ConsentSyncLog,
    Recipient,
    RecipientPreference,
)

# Re-exported for callers that imported it from here before consent moved into
# its own module. The gates now use app.recipients.consent directly.
__all__ = ["CONSENTING_STATUS"]


def suppress_recipient(
    db: Session,
    recipient_id: int,
    reason: str,
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
) -> bool:
    """Opt a recipient out because of a delivery-feedback signal (hard bounce /
    spam complaint) the provider reported. Idempotent — returns True only if the
    consent state actually changed.

    Writes a consent event with ``source="provider"``. The old implementation
    deliberately skipped the sync log so that drift would surface "provider
    suppressed someone the CRM still thinks is opted-in"; that trick is gone
    because it is no longer needed — a provider suppression is simply an event
    with a non-CRM source, and it shows as *platform-ahead* drift against the
    latest ``source="crm"`` event with no special-casing
    (ADR-163 addendum 2026-09-12, point 4).

    ``channel`` and ``purpose`` are parameters rather than assumptions: the
    caller reads them off the delivery execution, which carries both since the
    same addendum's point 1. A bounce on email says nothing about push."""
    recipient = db.query(RecipientDB).filter(RecipientDB.id == recipient_id).first()
    if recipient is None:
        return False
    current = latest_consent_status(db, recipient_id, channel=channel, purpose=purpose)
    if current == ConsentStatus.opted_out.value:
        return False  # already suppressed
    record_consent(
        db,
        recipient_id,
        ConsentStatus.opted_out.value,
        source="provider",
        channel=channel,
        purpose=purpose,
        note=reason,
    )
    return True

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


def to_recipient(db: Session, record: RecipientDB) -> Recipient:
    """Project a recipient row for the API.

    `consent_status` is no longer a column: it is resolved from the latest
    (email, marketing) consent event. The API keeps exposing a single scalar
    because that is what one channel's callers need today; a per-cell view is
    what `GET /recipients/consent/drift` gives, and a fuller grid belongs with
    the per-channel UI that does not exist yet.
    """
    return Recipient(
        id=record.id,
        external_id=record.external_id,
        email=record.email,
        language=record.language,
        attributes=record.attributes,
        status=record.status,
        consent_status=(
            latest_consent_status(db, record.id) or ConsentStatus.pending.value
        ),
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

    db.flush()

    # Consent is an event, not a field: only write one when this call actually
    # asserts a different state, so a routine re-sync does not pad the log with
    # rows saying nothing changed.
    if latest_consent_status(db, recipient.id) != consent_status:
        record_consent(
            db,
            recipient.id,
            consent_status,
            source="import",
            note=f"set via create_recipient for external_id={external_id}",
            commit=False,
        )

    # Addressability likewise: the email argument is an address on the email
    # channel (ADR-163 point 2). Phase A still writes RecipientDB.email above;
    # phase B removes that column and leaves only this.
    _upsert_email_address(db, recipient.id, email)

    db.commit()
    db.refresh(recipient)

    return to_recipient(db, recipient)


def _upsert_email_address(db: Session, recipient_id: int, email: str) -> None:
    """Keep the recipient's email-channel address row in step with the projection.

    Updates the existing primary row rather than appending a second one: a CRM
    re-sync that repeats the same address is not the person acquiring another
    inbox. Several addresses per channel are allowed (point 2) — they just do
    not arrive this way.
    """
    if not email:
        return
    existing = (
        db.query(AddressabilityDB)
        .filter(
            AddressabilityDB.recipient_id == recipient_id,
            AddressabilityDB.channel == DEFAULT_CHANNEL,
        )
        .order_by(
            AddressabilityDB.is_primary.desc(), AddressabilityDB.id.asc()
        )
        .first()
    )
    if existing is None:
        db.add(
            AddressabilityDB(
                recipient_id=recipient_id,
                channel=DEFAULT_CHANNEL,
                value={"email": email},
                status="active",
                is_primary=True,
            )
        )
    elif existing.value != {"email": email}:
        existing.value = {"email": email}
        existing.status = "active"


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

    before = latest_consent_status(
        db, recipient.id, channel=channel, purpose=purpose
    )
    changed = before != crm_consent_status
    if changed:
        record_consent(
            db,
            recipient.id,
            crm_consent_status,
            source=source,
            channel=channel,
            purpose=purpose,
            note=note,
            commit=False,
        )

    # The log records the conversation, not the value: it ran, it succeeded, it
    # applied N changes. The asserted value itself is the consent event above,
    # with source="crm" — storing it here too would be one fact in two places,
    # free to disagree (ADR-163 addendum 2026-09-12, point 2).
    db.add(
        ConsentSyncLogDB(
            recipient_id=recipient.id,
            external_id=external_id,
            ok=True,
            changes_applied=1 if changed else 0,
            source=source,
            note=note,
        )
    )
    db.commit()
    db.refresh(recipient)

    return to_recipient(db, recipient)


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
            ok=r.ok,
            changes_applied=r.changes_applied,
            source=r.source,
            note=r.note,
            synced_at=r.synced_at,
        )
        for r in rows
    ]


def detect_consent_drift(db: Session) -> list[ConsentDriftItem]:
    """Surface cells where the platform's consent disagrees with the CRM's last
    assertion, and say **which way**.

    Both sides now come from one table: the effective state is the latest event
    for a cell, and the CRM's assertion is the latest event for that cell with
    `source="crm"`. Storing the CRM's value separately would be the same fact
    twice (ADR-163 addendum 2026-09-12, point 2).

    Direction is the point, because the two cases need opposite actions and a
    boolean comparison makes them look identical
    (addendum point 4):

    * **platform_ahead** — something here (usually a provider bounce or spam
      complaint) opted someone out and the CRM has not been told. The fix flows
      *outward*: relay it, or the CRM keeps asserting a consent the person has
      withdrawn. This is the case the old code contrived a missing log row to
      expose.
    * **crm_ahead** — the CRM asserted something that never took effect here.
      The fix flows *inward*: re-run the sync. This is the original
      "CRM says no, platform still says yes" case.

    Reads the event log once and groups in Python rather than issuing a query
    per recipient, which is what the previous implementation did.
    """
    rows = (
        db.query(ConsentEventDB)
        .order_by(ConsentEventDB.created_at.asc(), ConsentEventDB.id.asc())
        .all()
    )

    # Walking oldest→newest leaves the newest per key in each map.
    latest: dict[tuple[int, str, str], ConsentEventDB] = {}
    latest_crm: dict[tuple[int, str, str], ConsentEventDB] = {}
    for row in rows:
        key = (row.recipient_id, row.channel, row.purpose)
        latest[key] = row
        if row.source == "crm":
            latest_crm[key] = row

    recipients = {
        r.id: r
        for r in db.query(RecipientDB)
        .filter(RecipientDB.id.in_({k[0] for k in latest_crm}))
        .all()
    } if latest_crm else {}

    drift: list[ConsentDriftItem] = []
    for key, crm_event in latest_crm.items():
        effective = latest[key]
        if effective.status == crm_event.status:
            continue
        recipient = recipients.get(key[0])
        if recipient is None:
            continue
        # If the newest event IS the CRM's, the CRM is the thing that is behind
        # only when something older-but-different is in force — which cannot
        # happen, since latest wins. So a disagreement means the effective
        # event is newer than the CRM's, i.e. the platform moved on its own.
        direction = (
            "platform_ahead"
            if effective.created_at >= crm_event.created_at
            else "crm_ahead"
        )
        drift.append(
            ConsentDriftItem(
                recipient_id=recipient.id,
                external_id=recipient.external_id,
                email=recipient.email,
                channel=key[1],
                purpose=key[2],
                platform_consent_status=effective.status,
                last_crm_consent_status=crm_event.status,
                last_synced_at=crm_event.created_at,
                direction=direction,
                platform_source=effective.source,
            )
        )
    return drift


def list_recipients(db: Session) -> list[Recipient]:
    records = db.query(RecipientDB).order_by(RecipientDB.id.asc()).all()
    return [to_recipient(db, record) for record in records]


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

    return to_recipient(db, record)


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