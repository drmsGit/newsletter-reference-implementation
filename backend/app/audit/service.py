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
import re

from sqlalchemy import or_
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
# task-358 (ADR-150 addendum 2026-10-16): the administration writes the Jinja
# forms never logged.
USER_CREATED = "user.created"
ROLE_CREATED = "role.created"
ROLE_PERMISSIONS_SET = "role.permissions_set"
ROLE_DELETED = "role.deleted"
BRAND_RENAMED = "brand.renamed"
BRAND_DELETED = "brand.deleted"
# Brand step 3. The audit log is how "where did this come from?" is answered —
# deliberately instead of a `copied_from_id` column, so the answer cannot go
# stale when the source is renamed, re-pointed or deleted. Same reasoning as
# ADR-163 computing consent from events rather than storing a status.
CAMPAIGN_DUPLICATED = "campaign.duplicated"
CONTENT_DUPLICATED = "content.duplicated"
VARIANT_DUPLICATED = "variant.duplicated"
# task-252: the composer's writes, both planes (ADR-153 point 4). A module
# delete names the overrides it erased, which is where their history survives
# (campaign write surface design pass, D2).
CAMPAIGN_CREATED = "campaign.created"
VARIANT_CREATED = "variant.created"
VARIANT_UPDATED = "variant.updated"
# task-254: a person (any fence) or a machine (its own) cleared a fence.
VARIANT_UNFENCED = "variant.unfenced"
MODULE_CREATED = "module.created"
MODULE_UPDATED = "module.updated"
MODULE_DELETED = "module.deleted"
MODULE_MOVED = "module.moved"
# task-290, ADR-187: a person hid or showed fields in a module (from/to lists).
MODULE_FIELDS_HIDDEN = "module.fields_hidden"
# task-295: every audience write (ADR-153 point 4; the Audience Write Surface
# final design pass, decision 10).
AUDIENCE_GROUP_CREATED = "audience_group.created"
AUDIENCE_GROUP_UPDATED = "audience_group.updated"
AUDIENCE_GROUP_DELETED = "audience_group.deleted"
AUDIENCE_RULE_ADDED = "audience_group.rule_added"
AUDIENCE_RULE_CHANGED = "audience_group.rule_changed"
AUDIENCE_RULE_REMOVED = "audience_group.rule_removed"
AUDIENCE_RULES_RECALCULATED = "audience_group.rules_recalculated"
AUDIENCE_MEMBER_ADDED = "audience_group.member_added"
AUDIENCE_MEMBER_REMOVED = "audience_group.member_removed"
AUDIENCE_PEOPLE_PASTED = "audience_group.people_pasted"
DECISION_SLOT_CREATED = "decision_slot.created"
DECISION_SLOT_UPDATED = "decision_slot.updated"
OVERRIDE_CREATED = "override.created"
OVERRIDE_RESET = "override.reset"
# task-256: an active override whose fields were changed in place.
OVERRIDE_CHANGED = "override.changed"
# task-257: catalogue edits, from the composer or the content screen, and
# publishing a version (which is what a send then uses).
CONTENT_UPDATED = "content.updated"
CONTENT_PUBLISHED = "content.published"
# task-275: the rest of the content writes, both planes (ADR-153 point 4).
# Category assignments feed slot ranking and every interest profile (ADR-080),
# so who set or removed one, at what score, is history worth keeping.
CONTENT_CREATED = "content.created"
CONTENT_STATUS_CHANGED = "content.status_changed"
CONTENT_DELETED = "content.deleted"
CONTENT_CATEGORY_ASSIGNED = "content.category_assigned"
CONTENT_CATEGORY_UNASSIGNED = "content.category_unassigned"
# task-359: the shared taxonomy's own writes. Categories belong to no brand
# (ADR-150), so the entry is the working brand's, where the person acted.
CATEGORY_CREATED = "category.created"
CATEGORY_CHANGED = "category.changed"
CATEGORY_DELETED = "category.deleted"
CATEGORY_RELATION_ADDED = "category.relation_added"
CATEGORY_RELATION_REMOVED = "category.relation_removed"
# task-278: a score changed in place (ADR-080's 2026-10-04 addendum).
CONTENT_CATEGORY_SCORE_CHANGED = "content.category_score_changed"
# task-283: readiness per channel and machine ready (ADR-174, ADR-179 addenda
# of 2026-10-05). The rows hold only the current mark; this log is the history.
CONTENT_READY_MARKED = "content.ready_marked"
CONTENT_READY_UNMARKED = "content.ready_unmarked"
CONTENT_MACHINE_READY_CHANGED = "content.machine_ready_changed"
# task-245: every settings write, both planes, and the access-control switch.
SETTINGS_CHANGED = "settings.changed"
# ADR-166's administration surface (task-50). Logged lines were the only trace
# of these until 2026-10-02; the subject is always the integration.
INTEGRATION_CREATED = "integration.created"
INTEGRATION_KEY_ISSUED = "integration.key_issued"
INTEGRATION_KEY_REVOKED = "integration.key_revoked"
INTEGRATION_KEY_EXPIRY_SET = "integration.key_expiry_set"
INTEGRATION_GRANT_ADDED = "integration.grant_added"
INTEGRATION_GRANT_REMOVED = "integration.grant_removed"
INTEGRATION_UNATTENDED_SET = "integration.unattended_set"
INTEGRATION_DEACTIVATED = "integration.deactivated"
# The approval lifecycle (ADR-142). Named here since 2026-10-08 (task-52);
# approvals/service.py keeps its short names as aliases of these.
APPROVAL_REQUESTED = "approval.requested"
APPROVAL_GRANTED = "approval.granted"
APPROVAL_REJECTED = "approval.rejected"
APPROVAL_EXPIRED = "approval.expired"
APPROVAL_FAILED = "approval.failed"
APPROVAL_WITHDRAWN = "approval.withdrawn"
# What a granted held action did, written by the action through ActionResult.
SEND_FIRED = "send.fired"
#: A consent change made by a person or an integration (task-340): who changed
#: it. The change itself is the consent event; this says who made it.
CONSENT_RECORDED = "consent.recorded"
# ADR-192: a person released a send stranded in "sending" (task-325).
SEND_RELEASED = "send.released"
AI_SUGGESTION_APPLIED = "ai.suggestion_applied"
# ADR-194, task-350. The detail names the fields that changed, never their
# values (addendum 2026-10-11, point 8): a legal address may hold an email.
BRAND_PROFILE_CREATED = "brand_profile.created"
BRAND_PROFILE_UPDATED = "brand_profile.updated"
BRAND_PROFILE_DUPLICATED = "brand_profile.duplicated"
BRAND_PROFILE_MADE_DEFAULT = "brand_profile.made_default"
BRAND_PROFILE_DELETED = "brand_profile.deleted"
ASSET_UPLOADED = "asset.uploaded"
ASSET_REPLACED = "asset.replaced"
ASSET_DESCRIBED = "asset.described"
ASSET_HIDDEN = "asset.hidden"
ASSET_COPIED = "asset.copied"
# ADR-199, task-365: a brand's expression dictionary. The detail names the
# entry, never a recipient's value.
EXPRESSION_CREATED = "expression.created"
EXPRESSION_UPDATED = "expression.updated"
EXPRESSION_DELETED = "expression.deleted"
# task-71: the demo reset emptied the demo data and built Grathaus. The
# entry is what remains of the history it removed (ADR-153: the log is kept).
DEMO_RESET = "demo.reset"

#: Every action name an entry may carry (task-52, ADR-153 addendum
#: 2026-10-08). Collected from the constants above, so adding one is still one
#: line; `record` refuses a name not in it, which turns a typo into an error
#: at the first write instead of a row no reader ever finds.
ACTIONS = frozenset(
    value for name, value in dict(globals()).items()
    if name.isupper() and isinstance(value, str) and "." in value
)

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


# Deliberately loose: anything shaped like an address is refused, so a label
# that merely looks like one is refused too. Phone numbers are not checked
# (too many false positives against ids and counts). A company address that
# must be recorded would need a named exemption here, decided, not added.
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

#: Top-level detail keys that hold authored copy, which the email check skips
#: (decided with the user 2026-10-08, task-52). A name, a title, a subject or
#: preheader is what a person wrote, not somebody's contact detail, and
#: "Reply to hello@brand.test" must not fail the save it records. Top level
#: only: a `name` nested deeper is not copy by that fact alone.
COPY_KEYS = frozenset({"name", "title", "envelope"})


def _detail_holds_an_email(detail: dict) -> bool:
    return any(_holds_an_email(key) or (key not in COPY_KEYS and _holds_an_email(value))
               for key, value in detail.items())


def _holds_an_email(value) -> bool:
    if isinstance(value, str):
        return bool(_EMAIL.search(value))
    if isinstance(value, dict):
        return any(_holds_an_email(k) or _holds_an_email(v) for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_holds_an_email(v) for v in value)
    return False


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

    **What an entry may say is checked before anything is written** (task-52,
    ADR-153 addendum 2026-10-08): the action must be in `ACTIONS`, and no
    value in the detail may be an email address — internal identifiers only
    (ADR-153 point 5), so erasing a person never has to rewrite the log;
    authored copy (`COPY_KEYS`) is exempt. Both raise ValueError: they are bugs
    in the caller, not database failures.

    Returns None on failure so a caller that cares can tell.
    """
    global _failures

    if action not in ACTIONS:
        raise ValueError(f"{action!r} is not an audit action; add it to the vocabulary in audit/service.py")
    if detail is not None and _detail_holds_an_email(detail):
        raise ValueError(f"an audit detail must not hold an email address ({action}); record the person's id")

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


def actor_of(request) -> tuple[str, int | None]:
    """Who is acting on this request, as `(actor_type, actor_id)` (task-340).

    The same answer `record_from_request` uses, for code that records further
    down, in a service that writes the thing being audited — a consent event is
    only written when the state changes, and only the service knows. An
    integration on the JSON plane is its own actor (ADR-166 point 3); otherwise
    the signed-in person, or None when nobody is.
    """
    from app.auth.db_models import IntegrationDB

    principal = getattr(request.state, "principal", None)
    if isinstance(principal, IntegrationDB):
        return ACTOR_INTEGRATION, principal.id
    user = request.state.current_user
    return ACTOR_USER, user["id"] if user else None


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
    db: Session, actor_id: int, actor_type: str = ACTOR_USER, limit: int = 50,
    brand_id: int | None = None,
) -> list[AuditEventDB]:
    """What one operator has done, newest first — ADR-153 point 1's screen.

    With `brand_id`, that brand's entries **and the ones with no brand**
    (task-52): a sign-in or a platform setting belongs to the person, not to
    any brand, and a plain `brand_id = X` would hide it from every brand's view.
    """
    query = db.query(AuditEventDB).filter(
        AuditEventDB.actor_type == actor_type,
        AuditEventDB.actor_id == actor_id,
    )
    if brand_id is not None:
        query = query.filter(or_(AuditEventDB.brand_id == brand_id, AuditEventDB.brand_id.is_(None)))
    return (
        query
        .order_by(AuditEventDB.created_at.desc(), AuditEventDB.id.desc())
        .limit(limit)
        .all()
    )
