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

import inspect
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.approvals.actions.base import ActionResult
from app.approvals.actions.registry import get_action, get_action_module
from app.approvals.db_models import (
    APPROVED, DECIDED, EXECUTING, EXPIRED, FAILED, PENDING, REJECTED, PendingActionDB,
)
from app.audit import service as audit

logger = logging.getLogger(__name__)

# The approval lifecycle's audit actions, by their short local names. The names
# themselves live in the one vocabulary in `audit/service.py` (task-52).
REQUESTED = audit.APPROVAL_REQUESTED
GRANTED = audit.APPROVAL_GRANTED
DENIED = audit.APPROVAL_REJECTED
LAPSED = audit.APPROVAL_EXPIRED
EXECUTION_FAILED = audit.APPROVAL_FAILED

#: The subject type every approval event points at.
SUBJECT = "pending_action"

#: Written as the actor of an expiry. Defined with the other actor kinds in
#: the audit module since 2026-10-01; re-exported here because callers and
#: tests already read it as `approvals.ACTOR_SYSTEM`.
ACTOR_SYSTEM = audit.ACTOR_SYSTEM


class DuplicateRequest(Exception):
    """There is already an open request for this action and subject."""


class NotApprovable(Exception):
    """The action key names nothing the registry knows about."""


class SubjectRequired(NotApprovable):
    """The request names no subject, so nothing could keep it one of a kind.

    task-15, ADR-142 addendum of 2026-09-29 (third). The one-open-request
    index is keyed on (action_key, subject_type, subject_id), and Postgres
    treats NULLs as distinct in a unique index — so a request without a
    subject is invisible to it, and two identical ones can both be open.
    """


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
    subject_scope: str = "",
) -> PendingActionDB:
    """Hold an action. The caller then **finishes** — nothing waits here.

    `subject_type` is taken from the action's declaration rather than the
    caller, so a request cannot claim to be about a kind of thing its action
    does not operate on.
    """
    meta = get_action(action_key)
    if meta is None:
        raise NotApprovable(action_key)

    # **Every held request names its subject** (task-15). The index that makes
    # a request one of a kind cannot see a NULL, and there are two ways to
    # produce one: an action that declares no subject — which is the dataclass
    # default, so forgetting is enough — and an action that declares one but
    # was handed no id, which the guard produces for a route whose path
    # parameter does not follow the `<subject_type>_id` convention.
    #
    # The one real subject-less case is ADR-142 §10 (AI proposing settings
    # changes), deliberately undesigned until after 1.0. Choosing what
    # identifies a settings proposal here — one per action, or a caller key —
    # would design §10 in advance. So this refuses, and §10 inherits the
    # question rather than a silent default.
    if not meta.subject_type:
        raise SubjectRequired(
            f"'{action_key}' declares no subject, so a held request for it could "
            "not be kept one of a kind. A subject-less action is the ADR-142 §10 "
            "case, which must decide what identifies such a request before one "
            "can be held."
        )
    if subject_id is None:
        raise SubjectRequired(
            f"a request for '{action_key}' names no {meta.subject_type}, so it "
            "could not be kept one of a kind. The subject is taken from the "
            f"path parameter named '{meta.subject_type}_id'."
        )
    if meta.subject_scope_param and not subject_scope:
        # The same refusal for the scope (task-206): an empty one is the slot
        # every unscoped action uses, so a scoped request without its value
        # would be held under the wrong key rather than refused.
        raise SubjectRequired(
            f"a request for '{action_key}' names no {meta.subject_scope_param}, so it "
            "could not be kept one of a kind. The scope is taken from the path "
            f"parameter named '{meta.subject_scope_param}'."
        )

    ttl = ttl_seconds if ttl_seconds is not None else meta.default_ttl_seconds
    row = PendingActionDB(
        action_key=action_key,
        payload=payload or {},
        summary=(summary or "").strip()[:500] or meta.label,
        requested_by_type=requested_by_type,
        requested_by_id=requested_by_id,
        subject_type=meta.subject_type,
        subject_id=subject_id,
        subject_scope=subject_scope or "",
        brand_id=brand_id,
        status=PENDING,
        # No deadline when the action type declares none (task-210): every
        # reader takes an empty expires_at as "never expires", not "expired".
        expires_at=None if ttl is None else now() + timedelta(seconds=ttl),
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

def _transition(
    db: Session, pending_id: int, *, from_status: str, to_status: str,
    also: tuple = (), **values,
) -> bool:
    """Move one row from one status to another, **only if it is still in the
    first**, and commit. True for exactly one caller.

    This replaces a row lock (ADR-142 addendum 2026-09-29, task-4). The lock
    was `SELECT … FOR UPDATE` held across `module.execute` — but the action runs
    on the same session, and `send_send_instance` commits inside it. That commit
    ended the transaction holding the lock while the row still read `pending`,
    so a second approver could claim it and execute again, stopped only by the
    send's own status guard — the masking the lock's docstring said it existed
    to prevent. A conditional UPDATE, committed before the action runs, cannot
    be released by anything the action does afterwards.

    `also` adds conditions to the WHERE — the claim uses it to refuse a request
    past its deadline by the database's clock.
    """
    moved = (
        db.query(PendingActionDB)
        .filter(
            PendingActionDB.id == pending_id,
            PendingActionDB.status == from_status,
            *also,
        )
        .update({"status": to_status, **values}, synchronize_session=False)
    )
    db.commit()
    return moved == 1


def _current(db: Session, pending_id: int) -> PendingActionDB | None:
    """The row as the database holds it now, not as this session last saw it."""
    db.expire_all()
    return db.get(PendingActionDB, pending_id)


def _approver_label(db: Session, approver_type: str, approver_id: int | None) -> str:
    """The approver as a record stores an actor in text (`actor_label`): a
    person's email, an integration's name."""
    from app.auth.db_models import IntegrationDB, UserDB
    from app.auth.service import actor_label

    model = (UserDB if approver_type == audit.ACTOR_USER
             else IntegrationDB if approver_type == audit.ACTOR_INTEGRATION else None)
    principal = db.get(model, approver_id) if model is not None and approver_id is not None else None
    return actor_label(principal)


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

    **Run-once is a claim, not a lock** (ADR-142 addendum 2026-09-29): the row
    moves `pending → executing`, committed, before the action runs, and only the
    caller whose move succeeded runs it and finalises it. Everybody else is told
    who got there first.

    Expiry is checked against `expires_at` and **not** against `status`, so a
    request cannot execute past its deadline on a machine where no sweeper has
    ever run — and the claim itself repeats that check in the database, so the
    deadline cannot pass between reading the row and claiming it.
    """
    row = _current(db, pending_id)
    if row is None:
        return ActionResult(ok=False, message="no such request")
    if row.status != PENDING:
        return ActionResult(ok=False, message=f"already {row.status}")
    if is_expired(row):
        # Retire it as part of refusing, so the inbox agrees with the answer the
        # caller just got.
        _expire(db, row)
        return ActionResult(ok=False, message="this request has expired")

    # Looked up BEFORE claiming: a request whose action is gone must stay
    # pending, not be claimed and then stranded in `executing` by a lookup
    # that was always going to fail.
    module = get_action_module(row.action_key)
    if module is None:
        return ActionResult(
            ok=False,
            message=f"'{row.action_key}' is no longer a registered action",
        )

    # The decision is recorded at the claim, because that is when the person
    # decided. `ck_pending_actions_decided` still means what it did: only
    # `pending` is undecided.
    claimed = _transition(
        db, pending_id, from_status=PENDING, to_status=EXECUTING,
        also=(or_(PendingActionDB.expires_at.is_(None),
                  PendingActionDB.expires_at > func.now()),),
        decided_at=now(), decided_by_type=approver_type,
        decided_by_id=approver_id, decision_reason=reason,
    )
    if not claimed:
        row = _current(db, pending_id)
        if row.status == PENDING:
            # Still pending, so the claim lost to the deadline, not to a
            # person — the one reason the WHERE refuses that leaves it here.
            _expire(db, row)
            return ActionResult(ok=False, message="this request has expired")
        return ActionResult(ok=False, message=f"already {row.status}")

    row = _current(db, pending_id)
    action_key, brand_id = row.action_key, row.brand_id
    subject_type, subject_id = row.subject_type, row.subject_id

    try:
        # **The brand the request was authorised in, not the approver's.**
        # An approver may hold grants on several brands and be looking at any
        # of them; the held action belongs to the one it was requested for,
        # which is the column on this row. Passing the approver's working brand
        # instead would let where somebody happened to be standing decide what
        # a queued send was allowed to touch.
        extra = {}
        if "approver" in inspect.signature(module.execute).parameters:
            # Only an action that asks is told who decided (task-206): the
            # readiness mark records the approver as the one who marked it
            # (ADR-174 addendum 2026-10-08). Asked, not imposed, so every
            # action written before this keeps its signature.
            extra["approver"] = _approver_label(db, approver_type, approver_id)
        result = module.execute(
            db, row.payload or {}, choice=choice, brand_id=brand_id, **extra,
        )
    except Exception as error:  # the action blew up
        db.rollback()
        # From EXECUTING only, and this caller holds the claim — so this can
        # only ever finalise our own run.
        _transition(
            db, pending_id, from_status=EXECUTING, to_status=FAILED,
            execution_error=str(error)[:1000],
        )
        audit.record(
            db, EXECUTION_FAILED,
            actor_type=approver_type, actor_id=approver_id,
            subject_type=SUBJECT, subject_id=pending_id, brand_id=brand_id,
            detail={"action_key": action_key, "error": str(error)[:500]},
        )
        logger.warning("pending action %s failed to execute", pending_id, exc_info=True)
        return ActionResult(ok=False, message=f"the action failed: {error}")

    if result.ok:
        _transition(db, pending_id, from_status=EXECUTING, to_status=APPROVED)
    else:
        # A clean refusal from the action itself — the send instance was already
        # sent, the content is unpublished. Recorded as FAILED rather than
        # REJECTED: nobody said no.
        _transition(
            db, pending_id, from_status=EXECUTING, to_status=FAILED,
            execution_error=(result.message or "the action declined to run")[:1000],
        )

    audit.record(
        db, GRANTED if result.ok else EXECUTION_FAILED,
        actor_type=approver_type, actor_id=approver_id,
        subject_type=SUBJECT, subject_id=pending_id, brand_id=brand_id,
        detail={"action_key": action_key, "reason": reason},
    )
    if result.ok and result.audit_action:
        # The action's own event, attributed to the APPROVER. This is where
        # ADR-140 §5's "approver-if-gated" lands — as the actor of the domain
        # event, rather than as a column on a domain table.
        audit.record(
            db, result.audit_action,
            actor_type=approver_type, actor_id=approver_id,
            subject_type=subject_type, subject_id=subject_id,
            brand_id=brand_id,
            detail={**(result.audit_detail or {}), "pending_action_id": pending_id},
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
    """Say no. The same conditional move as approving, so a rejection can never
    land on a request somebody else is already running."""
    row = _current(db, pending_id)
    if row is None:
        return False
    rejected = _transition(
        db, pending_id, from_status=PENDING, to_status=REJECTED,
        decided_at=now(), decided_by_type=approver_type,
        decided_by_id=approver_id, decision_reason=reason,
    )
    if not rejected:
        return False
    audit.record(
        db, DENIED,
        actor_type=approver_type, actor_id=approver_id,
        subject_type=SUBJECT, subject_id=pending_id, brand_id=row.brand_id,
        detail={"action_key": row.action_key, "reason": reason},
    )
    return True


# --- expiry -----------------------------------------------------------------

def _expire(db: Session, row: PendingActionDB) -> bool:
    """Retire a request that lapsed — **only if it is still pending** (task-13).

    It used to set the status on whatever ORM object it was handed and commit.
    A sweep could read a pending row, an approver could decide it, and the
    sweep then wrote `expired` over the decision from its stale copy: a request
    approved, executed and mailed, recorded as having lapsed. And two
    overlapping sweeps each emitted `approval.expired` for the same row. The
    conditional move gives exactly one caller the transition and the event.
    """
    expired = _transition(
        db, row.id, from_status=PENDING, to_status=EXPIRED,
        # `decided_by_*` stay NULL: nobody decided this.
        decided_at=now(),
    )
    if expired:
        audit.record(
            db, LAPSED,
            actor_type=ACTOR_SYSTEM, actor_id=None,
            subject_type=SUBJECT, subject_id=row.id, brand_id=row.brand_id,
            detail={"action_key": row.action_key},
        )
    return expired


def expire_due_pending_actions(db: Session) -> list[int]:
    """Retire everything past its deadline. Idempotent, and safe to run twice
    **concurrently** since 2026-09-29 — before, it was safe only one at a time.

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
    # Only the rows this sweep actually moved. Another sweep, or an approver,
    # may have taken some of `due` between the SELECT and here, and reporting
    # those as expired by this run would be the doubled event task-13 found.
    expired: list[int] = [row.id for row in due if _expire(db, row)]
    if expired:
        logger.info("expired %s pending action(s): %s", len(expired), expired)
    return expired


# --- reading ----------------------------------------------------------------

def requester_is_decider(user, row: PendingActionDB) -> bool:
    """Whether the person deciding this request is the one who made it.

    **Type as well as id.** `requested_by_id` is a bare integer with no foreign
    key — a machine principal's id and a person's id come from different tables,
    so comparing ids alone would eventually match two unrelated principals by
    coincidence. `requested_by_type` is what makes the comparison mean anything.

    Lives here rather than inline because two callers need the same answer and
    must not drift: `may_decide` gates the button, `resolve_for_decision` writes
    the sentence explaining why it is missing. That is the same reason
    `may_decide` itself was moved out of the Jinja router.
    """
    from app.audit.service import ACTOR_USER

    if user is None:
        return False
    return row.requested_by_type == ACTOR_USER and row.requested_by_id == user.id


def may_decide(db: Session, user, meta, row: PendingActionDB) -> bool:
    """Whether this person may approve or reject this particular request.

    **The real gate, and it lives here rather than in a router.** `policy.py`
    records why the policy table cannot express it: the permission depends on
    the *row* — every approvable action declares its own `approve_permission` —
    so the table maps the approve routes to `view` with a comment and this is
    what actually decides. Moved out of `app/frontend/router.py` on 2026-09-20,
    when the JSON plane needed the same answer: two planes asking one question
    is the whole point, and a second copy in a second router is how they start
    answering it differently.

    Brand-scoped permissions are checked against **the request's own brand**
    rather than the working one. They are the same today, because the inbox is
    filtered by working brand — but reading the row's brand is what stays
    correct if the inbox ever shows more than one, and it is the same rule
    `approve()` follows when it hands `execute` the row's brand.

    `user` is `None` only with access control switched off, where there is no
    principal to check anything against and the guard has already let the
    request through.
    """
    if user is None:
        from app.auth.dependencies import auth_enforced

        return not auth_enforced(db)

    if not meta.requester_may_decide and requester_is_decider(user, row):
        # Checked before the permission, because it is not a permission
        # question: this person may well hold `approve_permission` and still
        # not be the one to use it here. See `ApprovableAction`.
        return False

    from app.auth.permissions import is_brand_scoped
    from app.auth.service import ALL_BRANDS, has_permission

    if is_brand_scoped(meta.approve_permission):
        return has_permission(db, user, meta.approve_permission, brand_id=row.brand_id)
    # Platform-level: the union, named (task-16).
    return has_permission(db, user, meta.approve_permission, brand_id=ALL_BRANDS)


def resolve_for_decision(db: Session, pending_id: int, *, brand_id: int, user):
    """Find a request in this brand and say whether this person may decide it.

    Returns `(row, meta, refusal)`. `refusal` is a readable sentence when the
    answer is no, and `None` when the caller may proceed — so both planes
    render the same reason rather than inventing their own wording.

    A row outside the brand answers exactly as a missing one (ADR-172 point 6).
    """
    from app.approvals.actions.registry import get_action

    row = (
        db.query(PendingActionDB)
        .filter(PendingActionDB.id == pending_id, PendingActionDB.brand_id == brand_id)
        .first()
    )
    if row is None:
        return None, None, "That request does not exist in this brand."

    meta = get_action(row.action_key)
    if meta is None:
        return row, None, (
            f"'{row.action_key}' is no longer a registered action, so it cannot "
            "be approved. Reject it, or restore the action module."
        )
    if not meta.requester_may_decide and requester_is_decider(user, row):
        # Its own sentence, because the permission one would be false here —
        # this person has the permission and is refused for a different reason,
        # and "you need a permission you already hold" is the kind of message
        # that sends somebody to an administrator for an hour.
        return row, meta, (
            f"You requested this, and '{meta.label}' has to be decided by "
            "somebody else."
        )
    if not may_decide(db, user, meta, row):
        return row, meta, (
            f"You need the '{meta.approve_permission}' permission to decide this."
        )
    return row, meta, None


def _status_clause(status: str, at: datetime):
    """`effective_status` as SQL, so the inbox can page in the database (task-209).

    **The second implementation of "expired", kept beside the first on
    purpose**, because two of them are how they drift apart (`is_expired`'s
    docstring). `test_approvals_list` holds this to `effective_status`'s answers
    for every status shape, deadline boundary included: a `pending` row whose
    `expires_at` is at or before `at` reads as expired, exactly as `is_expired`
    decides it.
    """
    from sqlalchemy import and_, or_

    still_pending = and_(
        PendingActionDB.status == PENDING,
        or_(PendingActionDB.expires_at.is_(None), PendingActionDB.expires_at > at),
    )
    if status == PENDING:
        return still_pending
    lapsed = and_(PendingActionDB.status == PENDING, PendingActionDB.expires_at <= at)
    return or_(PendingActionDB.status.in_(DECIDED), lapsed)


def _inbox_query(
    db: Session, brand_id: int | None, status: str, *, action_key=None,
    requested_by_type=None, requested_by_id=None, at: datetime | None = None,
):
    """The inbox's filters, built once for the list AND its count, so the
    total can never be counted with different filters than the rows
    (ADR-185 point 6)."""
    query = db.query(PendingActionDB)
    if brand_id is not None:
        query = query.filter(PendingActionDB.brand_id == brand_id)
    if status != "all":
        query = query.filter(_status_clause(status, at or now()))
    if action_key is not None:
        query = query.filter(PendingActionDB.action_key == action_key)
    if requested_by_type is not None:
        query = query.filter(PendingActionDB.requested_by_type == requested_by_type)
    if requested_by_id is not None:
        query = query.filter(PendingActionDB.requested_by_id == requested_by_id)
    return query


def count_for_brand(db: Session, brand_id: int | None, status: str = PENDING, **filters) -> int:
    """How many requests `list_for_brand` would return without a limit —
    the `total` of the inbox's page (ADR-185)."""
    return _inbox_query(db, brand_id, status, **filters).count()


def list_for_brand(
    db: Session, brand_id: int | None, status: str = PENDING, *,
    action_key: str | None = None,
    requested_by_type: str | None = None,
    requested_by_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    at: datetime | None = None,
) -> list[PendingActionDB]:
    """The inbox query: one flat list, newest first (Manager Workflow Q1.3).

    `status="pending"` deliberately excludes a row whose deadline has passed but
    whose column has not caught up — the list must agree with what `approve()`
    would do, and `approve()` reads the timestamp.

    Narrowed by action type and by requester (ADR-166 point 3 makes the
    requester a durable actor, so "what did this integration send" is
    answerable), and paged with `limit`/`offset` **in the database** — the
    status rule is SQL for that reason (task-209). `limit=None` is every row,
    which is what the Jinja inbox asks for. `id` breaks ties so pages are stable.
    """
    query = _inbox_query(db, brand_id, status, action_key=action_key,
                         requested_by_type=requested_by_type,
                         requested_by_id=requested_by_id, at=at)
    if status == "decided":
        # The history reads by when each request ENDED (Manager Workflow Q1.6):
        # decided, or — for one that lapsed with nobody deciding — its deadline.
        from sqlalchemy import func

        ended = func.coalesce(PendingActionDB.decided_at, PendingActionDB.expires_at)
        query = query.order_by(ended.desc(), PendingActionDB.id.desc())
    else:
        query = query.order_by(PendingActionDB.created_at.desc(), PendingActionDB.id.desc())
    if offset:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def actor_names(db: Session, pairs) -> dict:
    """{(type, id): readable name} for requesters and deciders, in two queries.

    An integration's name; a person's display name, else email. One that no
    longer exists is named honestly ("integration #6") rather than dropped:
    the request it made is real history. Shown to anyone who may view the
    inbox — decided with the user 2026-10-03.
    """
    from app.auth.db_models import IntegrationDB, UserDB

    pairs = {(t, i) for t, i in pairs if t}
    user_ids = [i for t, i in pairs if t == "user" and i is not None]
    integration_ids = [i for t, i in pairs if t == "integration" and i is not None]
    known = {
        "user": {u.id: (u.display_name or u.email) for u in
                 db.query(UserDB).filter(UserDB.id.in_(user_ids or [-1]))},
        "integration": {i.id: i.name for i in
                        db.query(IntegrationDB).filter(IntegrationDB.id.in_(integration_ids or [-1]))},
    }
    return {
        (t, i): known.get(t, {}).get(i) or (f"{t} #{i}" if i is not None else t)
        for t, i in pairs
    }


def filter_options(db: Session, brand_id: int) -> dict:
    """What this brand's inbox can be narrowed by (2026-10-03).

    Drawn only from this brand's own requests, so it never says which actions
    or integrations exist elsewhere. Requesters are named because Q1.3's "what
    did Acme Agency send" is asked by name; the integrations list itself is
    `integrations.manage` only. A requester or action that no longer exists is
    still offered — its requests are real history — and named honestly.
    """
    from app.approvals.actions.registry import get_action

    keys = [k for (k,) in db.query(PendingActionDB.action_key)
            .filter(PendingActionDB.brand_id == brand_id).distinct()]
    actions = sorted(
        ({"key": k, "label": (get_action(k).label if get_action(k) else k)} for k in keys),
        key=lambda a: a["label"].lower(),
    )
    pairs = (db.query(PendingActionDB.requested_by_type, PendingActionDB.requested_by_id)
             .filter(PendingActionDB.brand_id == brand_id).distinct().all())
    names = actor_names(db, pairs)
    requesters = sorted(
        ({"type": t, "id": i, "name": names[(t, i)]} for t, i in pairs if (t, i) in names),
        key=lambda r: (r["type"], r["name"].lower()),
    )
    return {"actions": actions, "requesters": requesters}


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
        # A request with no deadline is pending for as long as nobody decides it.
        or_(PendingActionDB.expires_at.is_(None), PendingActionDB.expires_at > func.now()),
    )
    if brand_id is not None:
        query = query.filter(PendingActionDB.brand_id == brand_id)
    return query.scalar() or 0
