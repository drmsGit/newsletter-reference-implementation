"""Fire a planned send that a machine asked for — ADR-166 point 5.

The first real approvable action, and the one the whole mechanism was built
for: `ApprovalRequired` has been refusing machine sends since the machine plane
shipped, because there was nowhere to hold them.

**Shipped ahead of its caller, deliberately.** Nothing raises a request for this
yet — the guard rewiring that turns `ApprovalRequired` from a refusal into a
queue is a separate change, and it touches the order in which permissions are
checked, which is not something to fold into the same commit as a new file.
Until then this module is inert: it can be listed, described and executed, and
only a seeded row or a test reaches it.
"""

import logging

from sqlalchemy.orm import Session

from app.approvals.actions.base import (
    ActionDescription, ActionResult, ApprovableAction,
)
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB

logger = logging.getLogger(__name__)

META = ApprovableAction(
    key="send.fire_send_instance",
    label="Send a prepared campaign",
    # The same permission a person needs to fire a send themselves. Requesting
    # and approving happen to coincide here — a human who may send may approve
    # a machine's send — and they will not for every action, which is why the
    # contract asks each one rather than deriving it.
    approve_permission="sends.execute",
    # ADR-142 §4: "A held 'send the morning campaign' is worthless three days
    # later." Twenty-four hours is long enough to cover an overnight request and
    # a morning review, and short enough that a forgotten one dies before it
    # becomes a surprise.
    default_ttl_seconds=24 * 60 * 60,
    subject_type="send_instance",
    description=(
        "An orchestrator asked to fire a send it is not permitted to fire "
        "unattended. Approving sends it now."
    ),
)


def summarise(db: Session, send_instance_id: int) -> str:
    """The one line frozen onto the request at the moment it is made.

    Deliberately plain text and no identifiers a person cannot read: this is
    what an expired request will still show a year from now, long after the
    send instance it names may have been deleted.
    """
    send_instance = db.query(SendInstanceDB).filter(
        SendInstanceDB.id == send_instance_id
    ).first()
    if send_instance is None:
        return f"Send #{send_instance_id} (no longer present)"
    return f"Send “{send_instance.name}” (#{send_instance.id})"


def describe(db: Session, payload: dict) -> ActionDescription:
    """What the approver sees, computed **now**.

    The recipient count is read live rather than carried in the payload,
    because the number at request time is not the number that will be mailed —
    and the gap between the frozen summary and this panel is often the reason
    to say no.
    """
    send_instance_id = payload.get("send_instance_id")
    send_instance = db.query(SendInstanceDB).filter(
        SendInstanceDB.id == send_instance_id
    ).first()

    if send_instance is None:
        return ActionDescription(
            summary=f"Send #{send_instance_id} no longer exists.",
            warnings=["The send this request refers to has been deleted. "
                      "Rejecting it is the only sensible outcome."],
        )

    planned = db.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.send_instance_id == send_instance.id
    ).count()

    rows = [
        ("Send", f"{send_instance.name} (#{send_instance.id})"),
        ("Status", send_instance.status),
        ("Provider", send_instance.provider or "mock"),
        ("From", send_instance.from_address or "— not set —"),
        ("Audience", f"{planned} planned recipient(s)"),
        ("Audience resolution", send_instance.audience_resolution_mode),
    ]

    warnings = []
    if send_instance.status in ("sending", "sent"):
        warnings.append(
            f"This send is already {send_instance.status}. Approving will be "
            "refused rather than sending twice."
        )
    if send_instance.audience_resolution_mode == "rerun":
        warnings.append(
            "The audience is re-resolved at send time, so the number above is "
            "what matches now — not necessarily what will be mailed."
        )
    if planned == 0 and send_instance.audience_resolution_mode != "rerun":
        warnings.append("No recipients are planned for this send.")
    if (send_instance.provider or "mock") != "mock":
        warnings.append(
            f"This will send for real through {send_instance.provider}."
        )

    return ActionDescription(
        summary=f"Send “{send_instance.name}” to {planned} recipient(s).",
        rows=rows,
        warnings=warnings,
        link=f"/ui/deliveries/send-instances/{send_instance.id}",
    )


def execute(db: Session, payload: dict, *, choice: dict | None = None) -> ActionResult:
    """Approving is what sends it (ADR-142 §4).

    `send_send_instance` takes its own row lock and refuses an instance that is
    already sending or sent, so a double approval cannot double-send. That guard
    existing is **not** a reason for the approvals service to skip its own lock:
    the next action to be written may well have no such protection, and a lock
    that only works because of what it happens to call is not a lock.
    """
    from app.delivery.service import send_send_instance

    send_instance_id = payload.get("send_instance_id")
    if not send_instance_id:
        return ActionResult(ok=False, message="this request names no send")

    try:
        send_send_instance(db, send_instance_id)
    except ValueError as refusal:
        # A clean refusal from the send path — already sent, snapshot missing,
        # audience unresolvable. Not an exception the approver caused, so it is
        # reported rather than raised.
        return ActionResult(ok=False, message=str(refusal))

    send_instance = db.query(SendInstanceDB).filter(
        SendInstanceDB.id == send_instance_id
    ).first()
    return ActionResult(
        ok=True,
        message=(
            f"Sent: {send_instance.sent_count} delivered, "
            f"{send_instance.failed_count} failed, "
            f"{send_instance.excluded_count} excluded."
        ) if send_instance else "Sent.",
        audit_action="send.fired",
        audit_detail={"send_instance_id": send_instance_id},
    )
