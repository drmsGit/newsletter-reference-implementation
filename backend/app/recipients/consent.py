"""Consent and addressability primitives (ADR-163).

Consent is an append-only event log, latest row wins per
`(recipient, channel, purpose)`. Nothing here mutates a status: a change is a
new row, because a column cannot carry the source and timestamp that make
consent provable, and ADR-154 requires proof of consent to survive an erasure
in minimised form.

Two properties this module is responsible for, both fail-closed:

* **No event means no consent.** The absence of a decision is not a grant, so a
  recipient with no row for a cell is excluded — including by the SQL filter,
  where the scalar subquery returns NULL and `NULL = 'opted_in'` is not true.
* **The reason is recoverable.** `ConsentDenied` is raised rather than a bare
  `ValueError`, so a caller can tell a consent refusal apart from "the strategy
  resolved nothing". Conflating those two is the root of the open P0, where
  `send_send_instance` catches `ValueError` and continues.

`ConsentDenied` subclasses `ValueError` deliberately: every existing caller
still catches it, so this can land without a flag day, while new code can catch
the precise type. ADR-163 point 8 requires the exclusion *reason* to be
recorded, which this makes possible — the recording itself lands with the
exclusion stack.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB

# The system's only channel and purpose until a second one is built. Named
# constants rather than literals so the call sites already read correctly when
# push or transfer arrives — those are rows, not migrations (ADR-163 point 1).
DEFAULT_CHANNEL = "email"
DEFAULT_PURPOSE = "marketing"

# The only status that is a grant.
CONSENTING_STATUS = "opted_in"


class ConsentDenied(ValueError):
    """A recipient has no grant for this (channel, purpose).

    A ValueError subclass so existing `except ValueError` callers keep working
    unchanged; catch this type to distinguish a compliance refusal from an
    ordinary "nothing resolved".
    """

    def __init__(
        self,
        recipient_id: int,
        channel: str = DEFAULT_CHANNEL,
        purpose: str = DEFAULT_PURPOSE,
        status: str | None = None,
    ):
        self.recipient_id = recipient_id
        self.channel = channel
        self.purpose = purpose
        self.status = status
        super().__init__(
            f"Recipient {recipient_id} is not opted-in for "
            f"({channel}, {purpose}) — current consent is "
            f"{status or 'no recorded grant'!r}. Consent is gated at "
            "audience-resolution time and must not be bypassed."
        )


def record_consent(
    db: Session,
    recipient_id: int,
    status: str,
    *,
    source: str,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
    note: str | None = None,
    commit: bool = True,
) -> ConsentEventDB:
    """Append a consent event. Never updates an existing row.

    `source` is load-bearing rather than decorative: it is what separates a CRM
    assertion from a provider suppression from a signup form, and therefore
    what makes drift computable without the sync log storing consent values
    (ADR-163 addendum 2026-09-12, points 2 and 4).
    """
    event = ConsentEventDB(
        recipient_id=recipient_id,
        channel=channel,
        purpose=purpose,
        status=status,
        source=source,
        note=note,
    )
    db.add(event)
    if commit:
        db.commit()
    else:
        db.flush()
    return event


def latest_consent_event(
    db: Session,
    recipient_id: int,
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
    source: str | None = None,
) -> ConsentEventDB | None:
    """The newest event for one cell, or None if the cell has never been set.

    `source` narrows to one origin — `source="crm"` gives the CRM's last
    assertion, which is what drift compares against.
    """
    q = db.query(ConsentEventDB).filter(
        ConsentEventDB.recipient_id == recipient_id,
        ConsentEventDB.channel == channel,
        ConsentEventDB.purpose == purpose,
    )
    if source is not None:
        q = q.filter(ConsentEventDB.source == source)
    return q.order_by(
        ConsentEventDB.created_at.desc(), ConsentEventDB.id.desc()
    ).first()


def latest_consent_status(
    db: Session,
    recipient_id: int,
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
) -> str | None:
    event = latest_consent_event(
        db, recipient_id, channel=channel, purpose=purpose
    )
    return event.status if event is not None else None


def latest_consent_statuses(
    db: Session,
    recipient_ids: list[int],
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
) -> dict[int, str]:
    """`latest_consent_status` for many recipients in one query.

    A list view projecting N recipients would otherwise issue N consent
    queries — the same N+1 ADR-163 point 10 rules out for the exclusion stages,
    and just as avoidable here.
    """
    if not recipient_ids:
        return {}
    rows = (
        db.query(ConsentEventDB)
        .filter(
            ConsentEventDB.recipient_id.in_(recipient_ids),
            ConsentEventDB.channel == channel,
            ConsentEventDB.purpose == purpose,
        )
        .order_by(
            ConsentEventDB.created_at.desc(), ConsentEventDB.id.desc()
        )
        .all()
    )
    # Ordered newest-first, so the first row seen per recipient wins.
    latest: dict[int, str] = {}
    for row in rows:
        latest.setdefault(row.recipient_id, row.status)
    return latest


def is_consenting(
    db: Session,
    recipient_id: int,
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
) -> bool:
    return (
        latest_consent_status(
            db, recipient_id, channel=channel, purpose=purpose
        )
        == CONSENTING_STATUS
    )


def require_consent(
    db: Session,
    recipient_id: int,
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
) -> None:
    """Raise ConsentDenied unless this cell holds a grant."""
    status = latest_consent_status(
        db, recipient_id, channel=channel, purpose=purpose
    )
    if status != CONSENTING_STATUS:
        raise ConsentDenied(recipient_id, channel, purpose, status)


def consenting_status_expr(
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
):
    """A correlated scalar subquery giving the latest consent status per
    `RecipientDB` row, for use as a SQL filter in the audience gates.

    Kept as a subquery rather than resolved to a set of ids in Python so the
    gates stay a single query — the audience side is already flagged for N+1
    patterns, and materialising every consenting id would scale with the
    recipient table rather than with the segment.

    A recipient with no event yields NULL, and `NULL = 'opted_in'` is never
    true, so the filter is fail-closed by construction.
    """
    return (
        select(ConsentEventDB.status)
        .where(
            ConsentEventDB.recipient_id == RecipientDB.id,
            ConsentEventDB.channel == channel,
            ConsentEventDB.purpose == purpose,
        )
        .order_by(ConsentEventDB.created_at.desc(), ConsentEventDB.id.desc())
        .limit(1)
        .correlate(RecipientDB)
        .scalar_subquery()
    )


def is_consenting_filter(
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
):
    """The gate predicate: `.filter(is_consenting_filter())`."""
    return consenting_status_expr(channel, purpose) == CONSENTING_STATUS


# ---------------------------------------------------------------------------
# Addressability
# ---------------------------------------------------------------------------


def addresses_for(
    db: Session,
    recipient_id: int,
    *,
    channel: str = DEFAULT_CHANNEL,
    active_only: bool = True,
) -> list[AddressabilityDB]:
    """Every address a recipient has on a channel.

    This is what a **fan-out** channel uses: push buzzes every live token the
    person has, so there is nothing to pick (ADR-163 point 11).
    """
    q = db.query(AddressabilityDB).filter(
        AddressabilityDB.recipient_id == recipient_id,
        AddressabilityDB.channel == channel,
    )
    if active_only:
        q = q.filter(AddressabilityDB.status == "active")
    return q.order_by(
        AddressabilityDB.is_primary.desc(),
        AddressabilityDB.verified_at.desc().nullslast(),
        AddressabilityDB.created_at.desc(),
    ).all()


def resolve_address(
    db: Session,
    recipient_id: int,
    *,
    channel: str = DEFAULT_CHANNEL,
) -> AddressabilityDB | None:
    """The one address a **pick-one** channel should use, or None.

    ADR-163 point 11: the row flagged `is_primary` wins; with none flagged, the
    most-recently-verified wins. Deliberately never blocks on an unmade choice —
    a manager may pin one when recency is the wrong answer, and otherwise never
    has to think about it.
    """
    candidates = addresses_for(db, recipient_id, channel=channel)
    return candidates[0] if candidates else None


def address_value(address: AddressabilityDB | None, key: str = "email") -> str | None:
    """Pull a scalar out of an address's JSON value.

    Addresses are JSON because a push token, a postal address and an email are
    not the same shape; `key` is what the channel's adapter asks for.
    """
    if address is None or not isinstance(address.value, dict):
        return None
    value = address.value.get(key)
    return value if isinstance(value, str) and value else None


def resolve_email(db: Session, recipient_id: int) -> str | None:
    """The send address for the email channel, via the point 11 rules."""
    return address_value(resolve_address(db, recipient_id, channel="email"))


def resolve_addresses(
    db: Session,
    recipient_ids: list[int],
    *,
    channel: str = DEFAULT_CHANNEL,
) -> dict[int, AddressabilityDB]:
    """`resolve_address` for many recipients in one query.

    ADR-163 point 10 requires the exclusion stages to be set operations rather
    than per-recipient loops — audience resolution runs over whole segments, so
    resolving addresses one at a time is the N+1 the record explicitly rules
    out. Precedence is identical to `resolve_address`: primary flag first, then
    most-recently-verified.
    """
    if not recipient_ids:
        return {}
    rows = (
        db.query(AddressabilityDB)
        .filter(
            AddressabilityDB.recipient_id.in_(recipient_ids),
            AddressabilityDB.channel == channel,
            AddressabilityDB.status == "active",
        )
        .order_by(
            AddressabilityDB.is_primary.desc(),
            AddressabilityDB.verified_at.desc().nullslast(),
            AddressabilityDB.created_at.desc(),
        )
        .all()
    )
    # Ordered best-first, so the first row seen per recipient is the winner.
    resolved: dict[int, AddressabilityDB] = {}
    for row in rows:
        resolved.setdefault(row.recipient_id, row)
    return resolved


def resolve_emails(
    db: Session, recipient_ids: list[int]
) -> dict[int, str]:
    """Bulk `resolve_email`: recipient id → send address, skipping any with none."""
    resolved = resolve_addresses(db, recipient_ids, channel="email")
    out: dict[int, str] = {}
    for recipient_id, row in resolved.items():
        value = address_value(row)
        if value:
            out[recipient_id] = value
    return out
