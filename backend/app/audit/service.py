"""Writing and reading the accountability log (ADR-153).

**Written from routes, not from services.** The route knows who is acting —
`request.state.current_user`, resolved once by the middleware — and the service
layer takes a database session, not a request. Threading an actor through every
write signature was considered and rejected for this slice: `brand_id` was
threaded that way and it was right there, because a brand is a property of the
*data*; an actor is a property of the *request*, and passing it down would put
a request concern in the domain layer for the sake of one log.

**When a service writes an entry instead** (ADR-153 addendum 2026-10-01,
task-23). The rule above stopped holding when approvals landed, and was a
documented exception there rather than a stated pattern. The pattern: an entry
is written where the actor is KNOWN, and never where it would have to be
guessed. A route writes it from the request. A service writes it, with the
actor passed explicitly, only when no request carries the actor —

  * an event with no request at all — a sweep, a scheduled job — written as
    `ACTOR_SYSTEM` (`approval.expired`);
  * an event whose actor was resolved before any route handler ran — a
    machine's held request, refused inside a dependency, written as the
    integration (`approval.requested`);
  * a decision whose actor the service is handed — the approver.

The cost that remains: **a service called from a script or job that passes no
actor is not audited.** Nothing infers an actor; writing one requires saying
who it was.
"""
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.audit.db_models import AuditEventDB

logger = logging.getLogger(__name__)

# --- the vocabulary --------------------------------------------------------
# Constants rather than an enum column: a new event costs a line here, not a
# migration. Named as `subject.verb_past_tense` so the log reads as a sentence.
SIGNED_IN = "user.signed_in"
ROLE_GRANTED = "user.role_granted"
ROLE_REVOKED = "user.role_revoked"
USER_DEACTIVATED = "user.deactivated"
USER_REACTIVATED = "user.reactivated"
BRAND_CREATED = "brand.created"
# Brand step 3. The audit log is how "where did this come from?" is answered —
# deliberately instead of a `copied_from_id` column, so the answer cannot go
# stale when the source is renamed, re-pointed or deleted. Same reasoning as
# ADR-163 computing consent from events rather than storing a status.
CAMPAIGN_DUPLICATED = "campaign.duplicated"
CONTENT_DUPLICATED = "content.duplicated"
VARIANT_DUPLICATED = "variant.duplicated"
# ADR-166's administration surface (task-50). Logged lines were the only trace
# of these until 2026-10-02; the subject is always the integration.
INTEGRATION_CREATED = "integration.created"
INTEGRATION_KEY_ISSUED = "integration.key_issued"
INTEGRATION_KEY_REVOKED = "integration.key_revoked"
INTEGRATION_GRANT_ADDED = "integration.grant_added"
INTEGRATION_GRANT_REMOVED = "integration.grant_removed"
INTEGRATION_UNATTENDED_SET = "integration.unattended_set"
INTEGRATION_DEACTIVATED = "integration.deactivated"

# The three kinds of actor, together — the pattern in the module docstring
# names all three, so they live beside each other (task-23).
ACTOR_USER = "user"
#: ADR-166's machine principals. Written as the requester of a held action
#: (`approval.requested`), whose actor is resolved before any route runs.
ACTOR_INTEGRATION = "integration"
#: No person and no machine: a sweep or a scheduled job (`approval.expired`).
#: Nobody decided it, so attributing it to a person would be the same
#: dishonesty `record` refuses when it writes a null actor rather than
#: guessing one. Moved here from approvals/service.py on 2026-10-01.
ACTOR_SYSTEM = "system"


#: Audit writes the database refused, since this process started (task-22).
#: Process-local and reset on restart — a durable count cannot live in the
#: store that is failing. It turns "the log is incomplete" from a line nobody
#: watches into a number every failure line carries.
_failures = 0


def failure_count() -> int:
    return _failures


def record(
    db: Session,
    action: str,
    *,
    actor_type: str = ACTOR_USER,
    actor_id: int | None = None,
    subject_type: str | None = None,
    subject_id: int | None = None,
    brand_id: int | None = None,
    detail: dict | None = None,
    commit: bool = True,
) -> AuditEventDB | None:
    """Append one entry. **Never raises for a database failure.**

    An audit write must not be able to break the action it records. A failure
    here means the log is incomplete, which is bad; a failure that rolls back a
    role grant because its log entry would not write is worse, and it is the
    failure mode that gets audit logging switched off in production.

    **The entry is written inside a SAVEPOINT** (task-22). This used to call
    `db.rollback()` on the caller's session when it failed — destroying the
    transaction the swallow existed to protect, and with `commit=False`, which
    is exactly the case where the caller still holds uncommitted work. Now only
    the savepoint is rolled back: the caller's work survives, and with
    `commit=True` it is still committed, without the entry.

    **Only `SQLAlchemyError` is swallowed** — "the database refused the
    write". A bug in the calling code (a bad argument, a TypeError) raises like
    any other bug instead of reading as a log line while the app keeps working.
    Schema drift, the other case the bare `except` used to hide, is refused at
    startup now by ADR-181's ledger and full schema check.

    Returns None on failure so a caller that cares can tell.
    """
    global _failures

    event = AuditEventDB(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        brand_id=brand_id,
        detail=detail,
    )
    try:
        with db.begin_nested():
            db.add(event)
    except SQLAlchemyError as error:
        _failures += 1
        logger.error(
            "audit: failed to record %s — %s (%d audit write(s) failed since start)",
            action, error, _failures,
        )
        event = None
    if commit:
        # The caller's work, and the entry if it was written. A failure HERE is
        # the caller's own and is theirs to see — this function swallows only
        # its own write.
        db.commit()
    return event


def record_from_request(request, db: Session, action: str, **kwargs) -> AuditEventDB | None:
    """`record`, taking the actor from the request the middleware already resolved.

    The actor is deliberately allowed to be None: with access control switched
    off nobody is signed in, and recording "no actor" honestly beats
    attributing the action to somebody who did not take it.
    """
    # **A machine on the JSON plane is its own actor** (ADR-166 point 3: the
    # integration is the durable audit actor). `current_user` is the session's
    # person and is None for a bearer credential, so without this every
    # machine-made change was recorded as made by nobody. Only the JSON guard
    # sets `principal`; its absence is the Jinja plane's ordinary case.
    from app.auth.db_models import IntegrationDB

    principal = getattr(request.state, "principal", None)
    if isinstance(principal, IntegrationDB):
        resolved = getattr(request.state, "working_brand_id", None)
        kwargs.setdefault("brand_id", resolved)
        return record(
            db, action, actor_type=ACTOR_INTEGRATION, actor_id=principal.id, **kwargs
        )

    # **Read strictly, without a default** (task-23). `attach_current_user`
    # sets both of these on every request — None when nobody is signed in —
    # so a default was never needed, and it made a renamed middleware attribute
    # turn every actor into NULL silently: fail-open in the one field this
    # table exists for. Now that raises at the first audited request.
    user = request.state.current_user
    # **The resolved working brand first** (ADR-172 point 1). On the JSON
    # plane `current_brand` is the middleware's presentation summary and the
    # guard no longer overwrites it, so reading that alone would attribute a
    # machine's audit entry to whatever brand the session happened to carry.
    # Every caller of this is on the Jinja plane today, where the two agree —
    # and the SPA migration moves them, at which point an omission here would
    # be a very quiet wrong answer.
    brand = request.state.current_brand
    # This one keeps its default: only the JSON guard sets it, so on the
    # Jinja plane its absence is the ordinary case, not a renamed attribute.
    resolved = getattr(request.state, "working_brand_id", None)
    kwargs.setdefault(
        "brand_id", resolved if resolved is not None else (brand["id"] if brand else None)
    )
    return record(db, action, actor_id=user["id"] if user else None, **kwargs)


def events_for_subject(
    db: Session, subject_type: str, subject_id: int, limit: int = 50
) -> list[AuditEventDB]:
    """What has happened to one thing, newest first."""
    return (
        db.query(AuditEventDB)
        .filter(
            AuditEventDB.subject_type == subject_type,
            AuditEventDB.subject_id == subject_id,
        )
        .order_by(AuditEventDB.created_at.desc(), AuditEventDB.id.desc())
        .limit(limit)
        .all()
    )


def events_by_actor(
    db: Session, actor_id: int, actor_type: str = ACTOR_USER, limit: int = 50
) -> list[AuditEventDB]:
    """What one operator has done, newest first — ADR-153 point 1's screen."""
    return (
        db.query(AuditEventDB)
        .filter(
            AuditEventDB.actor_type == actor_type,
            AuditEventDB.actor_id == actor_id,
        )
        .order_by(AuditEventDB.created_at.desc(), AuditEventDB.id.desc())
        .limit(limit)
        .all()
    )
