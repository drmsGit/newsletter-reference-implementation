"""Mark a content record ready for a channel, as a machine asked — ADR-174 point 4.

An agency or an AI agent may say a record is ready for a channel; a person
decides it (Manager Workflow interview Q2.6b). A person's own mark is not held:
a person marking it *is* the approval. Built by task-206, decided with the user
2026-10-08 (addenda of that date to ADR-174 and ADR-142):

- **no deadline** — "is this copy good" does not go stale (task-210);
- **one request per record and channel** — the channel is the subject's scope,
  so an agency's email and push marks for one record are two requests;
- **the approver is recorded as the one who marked it** — the machine
  recommends, the person publishes (ADR-082); the integration that asked stays
  in the request's history and the audit log.

Reached through the guard: every integration's PUT on the mark route is held
(`HELD_FOR_EVERY_INTEGRATION` in `app/auth/policy.py`). Removing a mark is not
held (ADR-174 addendum 2026-10-05, point 5).
"""

from sqlalchemy.orm import Session

from app.approvals.actions.base import ActionDescription, ActionResult, ApprovableAction

META = ApprovableAction(
    key="content.mark_ready",
    label="Mark content ready for a channel",
    # What a person needs to mark a record ready themselves.
    approve_permission="content.manage",
    # ADR-142 addendum 2026-09-24: an action whose moment does not pass.
    default_ttl_seconds=None,
    # A machine asks and a person decides; were a person ever to ask, someone
    # else should say yes — the point of holding it at all.
    requester_may_decide=False,
    subject_type="content",
    subject_scope_param="channel",
    description=(
        "An integration said this record is ready for a channel. Approving marks it "
        "ready, in your name; until then no slot picks it for that channel."
    ),
)


def _record(db: Session, content_id: int, *, brand_id: int):
    from app.content.service import get_content_record

    return get_content_record(db, content_id, brand_id=brand_id)


def subject_in_brand(db: Session, content_id: int, *, brand_id: int) -> bool:
    """Asked before anything is held: a record of another brand holds nothing (task-9)."""
    return _record(db, content_id, brand_id=brand_id) is not None


def summarise(db: Session, content_id: int, *, brand_id: int) -> str:
    """The line frozen onto the request; it names the record, not the channel,
    which the payload keeps and the review shows."""
    record = _record(db, content_id, brand_id=brand_id)
    return f"“{record.title}” (#{record.id})" if record is not None else f"Content #{content_id} (no longer present)"


def describe(db: Session, payload: dict, *, brand_id: int) -> ActionDescription:
    """What the approver sees, now: the record, the channel, whether it is
    already marked, and the readiness warning — which informs and never blocks
    (ADR-174 point 2, addendum 2026-10-05 point 4)."""
    from app.channels.registry import get_channel
    from app.content.db_models import ContentChannelReadinessDB
    from app.content.service import readiness_warning

    content_id, channel = payload.get("content_id"), payload.get("channel")
    record = _record(db, content_id, brand_id=brand_id) if content_id is not None else None
    if record is None:
        return ActionDescription(
            summary=f"Content #{content_id} no longer exists.",
            blocked_reason="The record this request refers to is gone, so there is nothing to mark.",
        )
    if get_channel(channel) is None:
        return ActionDescription(
            summary=f"“{record.title}” for an unknown channel.",
            blocked_reason=f"There is no channel '{channel}' to mark it ready for.",
        )
    title = channel.capitalize()
    marked = (
        db.query(ContentChannelReadinessDB)
        .filter_by(content_id=record.id, channel=channel)
        .first()
    )
    warning = readiness_warning(record.content, channel)
    return ActionDescription(
        summary=f"Mark “{record.title}” ready for {title}",
        rows=[
            ("Content", record.title),
            ("Channel", title),
            ("Status", record.status),
            ("Already marked", f"by {marked.marked_by}" if marked is not None else "no"),
        ],
        warnings=[warning] if warning else [],
        link=f"/content/{record.id}",
    )


def execute(db: Session, payload: dict, *, choice=None, brand_id: int, approver: str) -> ActionResult:
    """Mark it ready in the approver's name. Marking a record already marked
    keeps the first mark, as a person's own second mark does."""
    from app.audit.service import CONTENT_READY_MARKED
    from app.content.service import mark_ready

    try:
        marked = mark_ready(db, payload["content_id"], payload["channel"], marked_by=approver, brand_id=brand_id)
    except LookupError as error:
        return ActionResult(ok=False, message=str(error))
    if marked is None:
        return ActionResult(ok=False, message="that record is gone")
    _, created = marked
    if not created:
        return ActionResult(ok=True, message="It was already marked ready; the first mark stays.")
    return ActionResult(ok=True, message=f"Marked ready for {payload['channel'].capitalize()}.",
                        audit_action=CONTENT_READY_MARKED, audit_detail={"channel": payload["channel"]})
