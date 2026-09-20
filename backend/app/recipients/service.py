from sqlalchemy.orm import Session

from app.recipients.consent import (
    CONSENTING_STATUS,
    DEFAULT_CHANNEL,
    address_key_for,
    address_value,
    addresses_for_many,
    consent_grid_many,
    DEFAULT_PURPOSE,
    latest_consent_event,
    latest_consent_status,
    latest_consent_statuses,
    record_consent,
    resolve_email,
    resolve_emails,
)
from app.recipients.db_models import (
    AddressabilityDB,
    ConsentEventDB,
    ConsentSyncLogDB,
    RecipientDB,
)
from app.recipients.models import (
    ConsentCell,
    ConsentDriftItem,
    ConsentStatus,
    ConsentSyncLog,
    Recipient,
    RecipientAddress,
    RecipientPreference,
)

# Re-exported for callers that imported it from here before consent moved into
# its own module. The gates now use app.recipients.consent directly.
__all__ = ["CONSENTING_STATUS"]


def suppress_recipient(
    db: Session,
    recipient_id: int,
    brand_id: int,
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
    current = latest_consent_status(
        db, recipient_id, brand_id, channel=channel, purpose=purpose
    )
    if current == ConsentStatus.opted_out.value:
        return False  # already suppressed for THIS brand
    record_consent(
        db,
        recipient_id,
        ConsentStatus.opted_out.value,
        brand_id,
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


def to_recipient(db: Session, record: RecipientDB, brand_id: int) -> Recipient:
    """Project one recipient row for the API.

    Neither the address nor the consent state is a column any more: the address
    is an addressability row (ADR-163 point 2, resolved by the point 11 rules)
    and the consent state is the latest event per cell — so the same recipient
    projects differently depending on which brand is asking, which is the point
    (ADR-163 addendum 2026-09-15).

    **The projection is per channel.** `addresses` and `consent` are the whole
    picture; `email` and `email_consent_status` are the email-channel views of
    it, named for their scope. The old flat `consent_status` was the (email,
    marketing) cell called "the" consent status, which was accurate while email
    was the only channel and became a lie the moment push existed — a contact
    that accepted notifications and was never asked about email projected as
    `pending`, true of the email cell and false of the person.

    Use `to_recipients` for more than one — this issues a fixed number of
    queries for the whole set, not per record.
    """
    return to_recipients(db, [record], brand_id)[0]


def to_recipients(db: Session, records: list[RecipientDB], brand_id: int) -> list[Recipient]:
    """Project many recipients with a fixed number of queries.

    Two lookups for the whole set rather than two per record. The consent
    lookup was already per-record before phase B and the address lookup would
    have doubled it; a list endpoint over a few hundred recipients would then
    issue several hundred queries to render one page.
    """
    if not records:
        return []
    from app.settings.service import available_channels

    ids = [record.id for record in records]
    channels = [c.name for c in available_channels(db)]
    # Four set-wide lookups, not four per record. The docstring's fixed-query
    # promise is the reason `consent_grid_many` and `addresses_for_many` exist
    # at all rather than looping the single-recipient readers.
    emails = resolve_emails(db, ids)
    consents = latest_consent_statuses(db, ids, brand_id)
    grids = consent_grid_many(db, ids, brand_id, channels)
    address_rows = addresses_for_many(db, ids)

    return [
        Recipient(
            id=record.id,
            external_id=record.external_id,
            # "" rather than None when there is no email address: the field is
            # non-optional in the API contract, and since ADR-167 a contact
            # whose only contact point is a device token is an ordinary state
            # rather than a broken record.
            email=emails.get(record.id, ""),
            language=record.language,
            attributes=record.attributes,
            status=record.status,
            email_consent_status=consents.get(record.id, ConsentStatus.pending.value),
            addresses=[
                RecipientAddress(
                    channel=row.channel,
                    # Through the channel's declared key, so a push row
                    # projects its token rather than an empty string.
                    value=address_value(row, address_key_for(row.channel)) or "",
                    status=row.status,
                )
                for row in address_rows.get(record.id, [])
            ],
            consent=[ConsentCell(**cell) for cell in grids.get(record.id, [])],
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record in records
    ]


def create_recipient(
    db: Session,
    brand_id: int,
    external_id: str,
    address: str = "",
    channel: str = DEFAULT_CHANNEL,
    language: str | None = None,
    attributes: dict | None = None,
    status: str = "active",
    consent_status: str = ConsentStatus.pending.value,
) -> Recipient:
    """Upserts keyed on external_id — a repeat CRM sync updates in place
    rather than hitting the unique constraint with a blind insert.

    **`address` and `channel`, not `email`.** [[ADR-167]] settles that a push
    audience arrives as ordinary contacts minted by the source system, so this
    path has to admit a recipient whose only contact point is a device token.
    It could not: `email` was a required positional, the address row was always
    written on the email channel, and — the sharper half — **the consent event
    was recorded with no channel at all**, so a synced contact was granted
    *email* consent whatever it had actually agreed to. That was invisible
    while email was the only channel, because the default was always right.

    **One address per call, deliberately.** A person with both an inbox and a
    device is two calls: the upsert is keyed on `external_id`, so the second
    updates the same recipient in place and asserts consent for its own
    channel. A list of addresses would be more general and would need rules
    for partial failure that nothing is asking for yet.
    """
    validate_recipient_attributes(attributes)

    recipient = (
        db.query(RecipientDB)
        .filter(RecipientDB.external_id == external_id)
        .first()
    )

    if recipient is None:
        recipient = RecipientDB(external_id=external_id)
        db.add(recipient)

    recipient.language = language
    recipient.attributes = attributes
    recipient.status = status

    db.flush()

    # Consent is an event, not a field: only write one when this call actually
    # asserts a different state, so a routine re-sync does not pad the log with
    # rows saying nothing changed.
    # Compared AND written on the same channel. Comparing against email while
    # writing email was self-consistent and wrong; comparing against one
    # channel and writing another would be worse, so both take `channel`.
    if latest_consent_status(db, recipient.id, brand_id, channel=channel) != consent_status:
        record_consent(
            db,
            recipient.id,
            consent_status,
            brand_id,
            source="import",
            channel=channel,
            note=f"set via create_recipient for external_id={external_id}",
            commit=False,
        )

    # The address is a row on its channel (ADR-163 point 2), and since phase B
    # it is the only place a contact point lives — there is no column on the
    # recipient to keep in step with it.
    _upsert_address(db, recipient.id, channel, address)

    db.commit()
    db.refresh(recipient)

    return to_recipient(db, recipient, brand_id)


def _upsert_address(db: Session, recipient_id: int, channel: str, address: str) -> None:
    """Keep this channel's address row in step with the projection.

    Updates the existing primary row rather than appending a second one: a CRM
    re-sync that repeats the same address is not the person acquiring another
    inbox. Several addresses per channel are allowed (point 2) — they just do
    not arrive this way.

    The JSON key comes from `address_key_for`, so the shape of a push row
    ({"token": …}) is not re-derived here. That mapping is the one place a new
    channel's address shape is taught, and it says so.
    """
    if not address:
        return
    value = {address_key_for(channel): address}
    existing = (
        db.query(AddressabilityDB)
        .filter(
            AddressabilityDB.recipient_id == recipient_id,
            AddressabilityDB.channel == channel,
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
                channel=channel,
                value=value,
                status="active",
                # Harmless on a fan-out channel: ADR-163 point 11 says push
                # "ignores it entirely". It matters only for pick-one channels.
                is_primary=True,
            )
        )
    elif existing.value != value:
        existing.value = value
        existing.status = "active"


def sync_consent_from_crm(
    db: Session,
    external_id: str,
    crm_consent_status: str,
    brand_id: int,
    source: str = "crm",
    note: str | None = None,
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
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
        db, recipient.id, brand_id, channel=channel, purpose=purpose
    )
    changed = before != crm_consent_status

    # The assertion is ALWAYS recorded, even when it matches what is already in
    # force. Two reasons, and the first is not an optimisation question:
    #
    #   * drift compares the effective state against the CRM's last assertion,
    #     so skipping an unchanged assertion leaves drift with no baseline —
    #     a later provider suppression would then be invisible, which is the
    #     exact failure this design exists to prevent;
    #   * the assertion is the evidence. "The CRM asserted opt-in on this date,
    #     from this source" is what defends a UWG §7 complaint, and it is not
    #     less true for having been asserted before.
    #
    # The cost is a row per sync rather than per change. Accepted: consent syncs
    # are low-frequency, and an append-only evidence log that omits evidence to
    # save rows is the wrong trade.
    record_consent(
        db,
        recipient.id,
        crm_consent_status,
        brand_id,
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

    return to_recipient(db, recipient, brand_id)


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

    drifting_ids = {k[0] for k in latest_crm}
    recipients = {
        r.id: r
        for r in db.query(RecipientDB).filter(RecipientDB.id.in_(drifting_ids)).all()
    } if latest_crm else {}
    # Addresses in one query, not one per drift row — the drift report is a
    # list view like any other.
    addresses = resolve_emails(db, sorted(drifting_ids)) if latest_crm else {}

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
                email=addresses.get(recipient.id, ""),
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


def list_recipients(db: Session, *, brand_id: int) -> list[Recipient]:
    """Every recipient, with consent projected against one brand.

    **The brand is required because consent is per-brand** (ADR-163's
    2026-09-15 addendum), so a recipient's consent status is not a fact until a
    brand is named. It is *context*, not authorisation: `recipients.manage`
    stays platform-level because recipients themselves carry no brand — the
    split ADR-172 point 1 makes available.

    This call passed two arguments to a three-argument function from the day
    `to_recipients` gained its brand until 2026-09-20, so `GET /recipients/`
    raised `TypeError` for every one of those days. Nothing in the repo called
    it, which is how a route that could not return went unnoticed; it was found
    by an unrelated test reaching for a platform-level route to assert against.
    """
    records = db.query(RecipientDB).order_by(RecipientDB.id.asc()).all()
    return to_recipients(db, records, brand_id)


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