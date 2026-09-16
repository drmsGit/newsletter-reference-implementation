"""Writing and reading the accountability log (ADR-153).

**Written from routes, not from services.** The route knows who is acting —
`request.state.current_user`, resolved once by the middleware — and the service
layer takes a database session, not a request. Threading an actor through every
write signature was considered and rejected for this slice: `brand_id` was
threaded that way and it was right there, because a brand is a property of the
*data*; an actor is a property of the *request*, and passing it down would put
a request concern in the domain layer for the sake of one log.

The cost is stated rather than discovered: **a service called from somewhere
other than a route is not audited.** Scripts, scheduled jobs and (when ADR-166
lands) machine callers all bypass this. That is acceptable while the log covers
human actions and nothing else, and it is the first thing to revisit when it
does not.
"""
import logging

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

ACTOR_USER = "user"
#: ADR-166's machine principals will use this. Nothing writes it yet.
ACTOR_INTEGRATION = "integration"


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
    """Append one entry. **Never raises.**

    An audit write must not be able to break the action it records. A failure
    here means the log is incomplete, which is bad; a failure that rolls back a
    role grant because its log entry would not write is worse, and it is the
    failure mode that gets audit logging switched off in production.

    So this swallows, and logs loudly at `error` — the one signal anyone gets,
    exactly as `deliver_code` does for a failed sign-in send. It returns None
    on failure so a caller that cares can tell.
    """
    try:
        event = AuditEventDB(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            brand_id=brand_id,
            detail=detail,
        )
        db.add(event)
        if commit:
            db.commit()
        else:
            db.flush()
        return event
    except Exception as error:  # noqa: BLE001 — see the docstring
        logger.error("audit: failed to record %s — %s", action, error)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


def record_from_request(request, db: Session, action: str, **kwargs) -> AuditEventDB | None:
    """`record`, taking the actor from the request the middleware already resolved.

    The actor is deliberately allowed to be None: with access control switched
    off nobody is signed in, and recording "no actor" honestly beats
    attributing the action to somebody who did not take it.
    """
    user = getattr(request.state, "current_user", None)
    brand = getattr(request.state, "current_brand", None)
    kwargs.setdefault("brand_id", brand["id"] if brand else None)
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
