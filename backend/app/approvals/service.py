"""Requesting, approving, rejecting and expiring held actions (ADR-142 §4).

**One convention this module breaks, deliberately and in writing.**
`app/audit/service.py` says audit is written from routes and not services,
"because the route knows who is acting". Approvals cannot honour that:
`approval.requested` is attributed to a machine that never reached a route
handler — it was refused inside a dependency — and `approval.expired` has no
request behind it at all. So this module writes its own audit entries with an
explicit actor. The audit service's own docstring already named this as "the
first thing to revisit when it does not hold", and this is that case.

**`status` is a cache; audit is the fact.** Every mutation here writes an
append-only entry first-class, and a test asserts that deleting every row in
`pending_actions` loses no accountability. That is what ADR-142 §4's "it extends
the ADR-140 audit surface; it is not a second log" costs in practice.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.approvals.actions.base import ActionResult
from app.approvals.actions.registry import get_action, get_action_module
from app.approvals.db_models import (
    APPROVED, DECIDED, EXPIRED, FAILED, PENDING, REJECTED, PendingActionDB,
)
from app.audit import service as audit

logger = logging.getLogger(__name__)

# The audit vocabulary for the approval lifecycle. Constants rather than an enum
# column, the same reasoning `audit/service.py` gives: a new event costs a line
# here, not a migration.
REQUESTED = "approval.requested"
GRANTED = "approval.granted"
DENIED = "approval.rejected"
LAPSED = "approval.expired"
EXECUTION_FAILED = "approval.failed"

#: The subject type every approval event points at.
SUBJECT = "pending_action"

#: Written as the actor of an expiry. Nobody decided it, so attributing it to a
#: person would be the same dishonesty `audit.record` refuses when it writes a
#: null actor rather than guessing one.
ACTOR_SYSTEM = "system"


class DuplicateRequest(Exception):
    """There is already an open request for this action and subject."""


class NotApprovable(Exception):
    """The action key names nothing the registry knows about."""


def now() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(row: PendingActionDB, at: datetime | None = None) -> bool:
    """Whether this request is past its deadline.

    **`expires_at` is authoritative; `status` is a cache.** No sweeper is
    scheduled — expiry bookkeeping runs from a route the way due sends do — so a
    row can sit at `pending` with a deadline in the past until somebody presses
    the button. Reading expiry from the timestamp means the screen is never
    wrong while the column is merely behind.

    One helper, used by both the guard and the list view, because two
    implementations of "expired" is precisely how the two drift apart.
    """
    if row.expires_at is None:
        return False
    deadline = row.expires_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return deadline <= (at or now())


def effective_status(row: PendingActionDB, at: datetime | None = None) -> str:
    """What to display. `pending` past its deadline reads as `expired`."""
    if row.status == PENDING and is_expired(row, at):
        return EXPIRED
    return row.status


# --- requesting -------------------------------------------------------------

def request_approval(
    db: Session,
    action_key: str,
    *,
    payload: dict,
    summary: str,
    requested_by_type: str,
    requested_by_id: int | None = None,
    brand_id: int | None = None,
    subject_id: int | None = None,
    ttl_seconds: int | None = None,
) -> PendingActionDB:
    """Hold an action. The caller then **finishes** — nothing waits here.

    `subject_type` is taken from the action's declaration rather than the
    caller, so a request cannot claim to be about a kind of thing its action
    does not operate on.
    """
    meta = get_action(action_key)
    if meta is None:
        raise NotApprovable(action_key)

    ttl = ttl_seconds if ttl_seconds is not None else meta.default_ttl_seconds
    row = PendingActionDB(
        action_key=action_key,
        payload=payload or {},
        summary=(summary or "").strip()[:500] or meta.label,
        requested_by_type=requested_by_type,
        requested_by_id=requested_by_id,
        subject_type=meta.subject_type,
        subject_id=subject_id,
        brand_id=brand_id,
        status=PENDING,
        expires_at=now() + timedelta(seconds=ttl),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # The partial unique index fired: an orchestrator retried a refused
        # call and would otherwise have produced a second held send for the
        # same instance. A friendly refusal, not a 500.
        db.rollback()
        raise DuplicateRequest(
            f"a request for {action_key} on {meta.subject_type} {subject_id} "
            "is already waiting"
        )
    db.refresh(row)

    audit.record(
        db, REQUESTED,
        actor_type=requested_by_type, actor_id=requested_by_id,
        subject_type=SUBJECT, subject_id=row.id, brand_id=brand_id,
        detail={
            "action_key": action_key,
            "subject_type": meta.subject_type,
            "subject_id": subject_id,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        },
    )
    logger.info(
        "approval requested: %s on %s %s (pending_action %s)",
        action_key, meta.subject_type, subject_id, row.id,
    )
    return row


# --- deciding ---------------------------------------------------------------

def _claim(db: Session, pending_id: int) -> PendingActionDB | None:
    """Lock the row so two operators clicking Approve cannot both win.

    Its own lock, and not a reliance on whatever the action's `execute` locks.
    `send_send_instance` happens to take a row lock of its own, which would mask
    the absence of this one — and the first action whose execution is not
    idempotent would then double-execute silently.
    """
    return (
        db.query(PendingActionDB)
        .filter(PendingActionDB.id == pending_id)
        .with_for_update()
        .first()
    )


def approve(
    db: Session,
    pending_id: int,
    *,
    approver_type: str,
    approver_id: int | None,
    choice: dict | None = None,
    reason: str | None = None,
) -> ActionResult:
    """Run the held action, and record who let it run.

    Expiry is checked against `expires_at` and **not** against `status`, so a
    request cannot execute past its deadline on a machine where no sweeper has
    ever run.
    """
    row = _claim(db, pending_id)
    if row is None:
        return ActionResult(ok=False, message="no such request")
    if row.status != PENDING:
        db.rollback()
        return ActionResult(ok=False, message=f"already {row.status}")
    if is_expired(row):
        # Retire it as part of refusing, so the inbox agrees with the answer the
        # caller just got.
        _mark_expired(db, row)
        return ActionResult(ok=False, message="this request has expired")

    module = get_action_module(row.action_key)
    if module is None:
        db.rollback()
        return ActionResult(
            ok=False,
            message=f"'{row.action_key}' is no longer a registered action",
        )

    try:
        result = module.execute(db, row.payload or {}, choice=choice)
    except Exception as error:  # the action blew up
        db.rollback()
        row = _claim(db, pending_id)
        row.status = FAILED
        row.decided_at = now()
        row.decided_by_type = approver_type
        row.decided_by_id = approver_id
        row.decision_reason = reason
        row.execution_error = str(error)[:1000]
        db.commit()
        audit.record(
            db, EXECUTION_FAILED,
            actor_type=approver_type, actor_id=approver_id,
            subject_type=SUBJECT, subject_id=row.id, brand_id=row.brand_id,
            detail={"action_key": row.action_key, "error": str(error)[:500]},
        )
        logger.warning("pending action %s failed to execute", pending_id, exc_info=True)
        return ActionResult(ok=False, message=f"the action failed: {error}")

    if not result.ok:
        # A clean refusal from the action itself — the send instance was already
        # sent, the content is unpublished. Recorded as FAILED rather than
        # REJECTED: nobody said no.
        row.status = FAILED
        row.execution_error = (result.message or "the action declined to run")[:1000]
    else:
        row.status = APPROVED
    row.decided_at = now()
    row.decided_by_type = approver_type
    row.decided_by_id = approver_id
    row.decision_reason = reason
    db.commit()

    audit.record(
        db, GRANTED if result.ok else EXECUTION_FAILED,
        actor_type=approver_type, actor_id=approver_id,
        subject_type=SUBJECT, subject_id=row.id, brand_id=row.brand_id,
        detail={"action_key": row.action_key, "reason": reason},
    )
    if result.ok and result.audit_action:
        # The action's own event, attributed to the APPROVER. This is where
        # ADR-140 §5's "approver-if-gated" lands — as the actor of the domain
        # event, rather than as a column on a domain table.
        audit.record(
            db, result.audit_action,
            actor_type=approver_type, actor_id=approver_id,
            subject_type=row.subject_type, subject_id=row.subject_id,
            brand_id=row.brand_id,
            detail={**(result.audit_detail or {}), "pending_action_id": row.id},
        )
    return result


def reject(
    db: Session,
    pending_id: int,
    *,
    approver_type: str,
    approver_id: int | None,
    reason: str | None = None,
) -> bool:
    row = _claim(db, pending_id)
    if row is None or row.status != PENDING:
        db.rollback()
        return False
    row.status = REJECTED
    row.decided_at = now()
    row.decided_by_type = approver_type
    row.decided_by_id = approver_id
    row.decision_reason = reason
    db.commit()
    audit.record(
        db, DENIED,
        actor_type=approver_type, actor_id=approver_id,
        subject_type=SUBJECT, subject_id=row.id, brand_id=row.brand_id,
        detail={"action_key": row.action_key, "reason": reason},
    )
    return True


# --- expiry -----------------------------------------------------------------

def _mark_expired(db: Session, row: PendingActionDB) -> None:
    row.status = EXPIRED
    # `decided_*` stay NULL: nobody decided this.
    row.decided_at = now()
    db.commit()
    audit.record(
        db, LAPSED,
        actor_type=ACTOR_SYSTEM, actor_id=None,
        subject_type=SUBJECT, subject_id=row.id, brand_id=row.brand_id,
        detail={"action_key": row.action_key},
    )


def expire_due_pending_actions(db: Session) -> list[int]:
    """Retire everything past its deadline. Idempotent, and safe to run twice.

    Bookkeeping only — `approve()` already refuses an expired request whatever
    this has or has not done. Modelled on `process_due_scheduled_sends`: the
    comparison happens in the database so the application's clock and the
    database's cannot disagree about what is due.
    """
    due = (
        db.query(PendingActionDB)
        .filter(
            PendingActionDB.status == PENDING,
            PendingActionDB.expires_at <= func.now(),
        )
        .all()
    )
    expired: list[int] = []
    for row in due:
        _mark_expired(db, row)
        expired.append(row.id)
    if expired:
        logger.info("expired %s pending action(s): %s", len(expired), expired)
    return expired


# --- reading ----------------------------------------------------------------

def list_for_brand(
    db: Session, brand_id: int | None, status: str = PENDING,
) -> list[PendingActionDB]:
    """The inbox query.

    `status="pending"` deliberately excludes a row whose deadline has passed but
    whose column has not caught up — the list must agree with what `approve()`
    would do, and `approve()` reads the timestamp.
    """
    query = db.query(PendingActionDB)
    if brand_id is not None:
        query = query.filter(PendingActionDB.brand_id == brand_id)

    rows = query.order_by(PendingActionDB.created_at.desc()).all()
    if status == "all":
        return rows
    if status == PENDING:
        return [r for r in rows if effective_status(r) == PENDING]
    return [r for r in rows if effective_status(r) in DECIDED]


def due_count(db: Session) -> int:
    """How many requests are past their deadline and not yet retired.

    Not brand-scoped, because the sweep it labels is not: a deadline is a time,
    not a brand, and an expired request is already refused in every brand
    whatever this column says. The same shape as
    `process_due_scheduled_sends`, which this borrows wholesale.
    """
    return db.query(func.count(PendingActionDB.id)).filter(
        PendingActionDB.status == PENDING,
        PendingActionDB.expires_at <= func.now(),
    ).scalar() or 0


def pending_count(db: Session, brand_id: int | None) -> int:
    """The nav badge. One indexed count, never a load-and-filter.

    The deadline comparison runs in the database rather than through
    `effective_status`, so this stays a count even when the inbox is long — and
    it gives the same answer, because both read `expires_at` rather than the
    status column.
    """
    query = db.query(func.count(PendingActionDB.id)).filter(
        PendingActionDB.status == PENDING,
        PendingActionDB.expires_at > func.now(),
    )
    if brand_id is not None:
        query = query.filter(PendingActionDB.brand_id == brand_id)
    return query.scalar() or 0
