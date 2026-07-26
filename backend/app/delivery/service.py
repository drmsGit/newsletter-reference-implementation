import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.models import DeliveryExecution, SendInstance

from app.campaigns.db_models import VariantDB
from app.delivery.providers.factory import get_provider
from app.recipients.db_models import RecipientDB
from app.rendering.service import render_variant_html
from app.snapshots.db_models import SnapshotDB

logger = logging.getLogger(__name__)


def to_delivery_execution(record: DeliveryExecutionDB) -> DeliveryExecution:
    return DeliveryExecution(
        id=record.id,
        send_instance_id=record.send_instance_id,
        recipient_id=record.recipient_id,
        status=record.status,
        provider=record.provider,
        provider_message_id=record.provider_message_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def create_delivery_execution(
    db: Session,
    send_instance_id: int,
    recipient_id: int,
    status: str = "created",
    provider: str | None = None,
    provider_message_id: str | None = None,
) -> DeliveryExecution:
    execution = DeliveryExecutionDB(
        send_instance_id=send_instance_id,
        recipient_id=recipient_id,
        status=status,
        provider=provider,
        provider_message_id=provider_message_id,
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    return to_delivery_execution(execution)


def list_delivery_executions_for_send_instance(
    db: Session,
    send_instance_id: int,
) -> list[DeliveryExecution]:
    records = (
        db.query(DeliveryExecutionDB)
        .filter(DeliveryExecutionDB.send_instance_id == send_instance_id)
        .order_by(DeliveryExecutionDB.created_at.desc())
        .all()
    )

    return [to_delivery_execution(record) for record in records]


def to_send_instance(record: SendInstanceDB) -> SendInstance:
    return SendInstance(
        id=record.id,
        snapshot_id=record.snapshot_id,
        name=record.name,
        status=record.status,
        provider=record.provider,
        scheduled_at=record.scheduled_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def create_send_instance(
    db: Session,
    snapshot_id: int,
    name: str,
    status: str = "draft",
    provider: str | None = None,
    scheduled_at=None,
    audience_group_id: int | None = None,
    from_address: str | None = None,
) -> SendInstance:
    send_instance = SendInstanceDB(
        snapshot_id=snapshot_id,
        name=name,
        status=status,
        provider=provider,
        scheduled_at=scheduled_at,
        audience_group_id=audience_group_id,
        from_address=from_address,
    )

    db.add(send_instance)
    db.commit()
    db.refresh(send_instance)

    return to_send_instance(send_instance)


def prepare_send_from_audience(
    db: Session,
    snapshot_id: int,
    name: str,
    audience_group_id: int,
    provider: str,
    from_address: str | None = None,
    audience_resolution_mode: str = "freeze",
    scheduled_at=None,
) -> SendInstanceDB:
    """Materialize a planned send: resolve the audience group to its live
    recipient set (consent-gated) and create one DeliveryExecution per
    recipient, all in status "created". Nothing is sent here. Raises ValueError
    on an empty audience or one exceeding the recipient cap.

    Two audience-resolution modes (`audience_resolution_mode`):
      "freeze" — the executions created here are final; a later edit to the
                 group's rules doesn't change who the send goes to.
      "rerun"  — these executions are a preview; the group is re-resolved and
                 reconciled immediately before the send fires (see
                 reconcile_executions_to_audience).

    `scheduled_at` set → status "scheduled" (fires later via
    process_due_scheduled_sends); otherwise "draft" (fires on manual Trigger)."""
    # Imported here rather than at module load to keep the delivery→audience
    # dependency local (audience never imports delivery).
    from app.audience.service import resolve_audience
    from app.settings.service import get_max_send_recipients

    if audience_resolution_mode not in ("freeze", "rerun"):
        raise ValueError("audience_resolution_mode must be 'freeze' or 'rerun'")

    # A naive scheduled_at (e.g. from a datetime-local input, local wall-clock)
    # must be made timezone-aware before it hits the timestamptz column —
    # otherwise Postgres reinterprets it in the session TZ and the "<= now()"
    # due-check drifts by the UTC offset. astimezone() attaches the local tz.
    if scheduled_at is not None and scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.astimezone()

    recipients = resolve_audience(db, audience_group_id)
    if not recipients:
        raise ValueError(
            "The selected audience resolves to 0 consenting recipients — nothing to send."
        )

    cap = get_max_send_recipients(db)
    if len(recipients) > cap:
        raise ValueError(
            f"The selected audience has {len(recipients)} recipients, over the send cap of {cap}. "
            "Raise the cap in Settings or narrow the audience."
        )

    send_instance = SendInstanceDB(
        snapshot_id=snapshot_id,
        name=name,
        status="scheduled" if scheduled_at else "draft",
        provider=provider,
        audience_group_id=audience_group_id,
        from_address=from_address or None,
        audience_resolution_mode=audience_resolution_mode,
        scheduled_at=scheduled_at,
    )
    db.add(send_instance)
    db.flush()  # assign send_instance.id before creating child executions

    for recipient in recipients:
        db.add(
            DeliveryExecutionDB(
                send_instance_id=send_instance.id,
                recipient_id=recipient.id,
                status="created",
                provider=provider,
            )
        )

    db.commit()
    db.refresh(send_instance)
    return send_instance


def reconcile_executions_to_audience(db: Session, send_instance: SendInstanceDB) -> None:
    """For a "rerun" send: re-resolve the audience group right before firing and
    reconcile executions — add one for each newly-matching recipient, and drop
    executions for recipients who no longer match *and* haven't sent yet (an
    already-sent execution is history and is left as-is). Enforces the recipient
    cap on the freshly-resolved set. No-op if the send has no audience group."""
    if not send_instance.audience_group_id:
        return

    from app.audience.service import resolve_audience
    from app.settings.service import get_max_send_recipients

    resolved_ids = {r.id for r in resolve_audience(db, send_instance.audience_group_id)}

    cap = get_max_send_recipients(db)
    if len(resolved_ids) > cap:
        raise ValueError(
            f"Re-resolved audience has {len(resolved_ids)} recipients, over the send cap of {cap}."
        )

    existing = (
        db.query(DeliveryExecutionDB)
        .filter(DeliveryExecutionDB.send_instance_id == send_instance.id)
        .all()
    )
    existing_by_recipient = {e.recipient_id: e for e in existing}

    # Drop no-longer-matching that haven't sent.
    for execution in existing:
        if execution.recipient_id not in resolved_ids and execution.status == "created":
            db.delete(execution)

    # Add newly-matching.
    for recipient_id in resolved_ids:
        if recipient_id not in existing_by_recipient:
            db.add(
                DeliveryExecutionDB(
                    send_instance_id=send_instance.id,
                    recipient_id=recipient_id,
                    status="created",
                    provider=send_instance.provider,
                )
            )

    db.commit()


def process_due_scheduled_sends(db: Session) -> list[int]:
    """Fire every scheduled send whose time has arrived. This is the operation a
    scheduler drives — a cron job, worker, or automation platform (n8n) calls it
    on an interval; the architecture just exposes the seam rather than baking in
    a specific scheduler. Returns the ids of the send instances it triggered."""
    due = (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.status == "scheduled",
            SendInstanceDB.scheduled_at.isnot(None),
            SendInstanceDB.scheduled_at <= func.now(),  # DB-side comparison avoids tz drift
        )
        .all()
    )
    triggered = []
    for send_instance in due:
        try:
            send_send_instance(db, send_instance_id=send_instance.id)
            triggered.append(send_instance.id)
        except Exception:
            logger.exception("scheduled send failed: send_instance_id=%s", send_instance.id)
    return triggered


def list_send_instances_for_snapshot(
    db: Session,
    snapshot_id: int,
) -> list[SendInstance]:
    records = (
        db.query(SendInstanceDB)
        .filter(SendInstanceDB.snapshot_id == snapshot_id)
        .order_by(SendInstanceDB.created_at.desc())
        .all()
    )

    return [to_send_instance(record) for record in records]


def send_send_instance(
    db: Session,
    send_instance_id: int,
):
    # Row lock + status guard: two concurrent calls both reading "draft"
    # before either commits would otherwise both proceed to send. FOR UPDATE
    # serializes the read-check-write of the status transition itself — the
    # second caller blocks here, then re-reads the row (now "sending"/"sent")
    # once the first commits, and gets rejected below instead of also sending.
    send_instance = (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.id == send_instance_id
        )
        .with_for_update()
        .first()
    )

    if send_instance is None:
        raise ValueError(
            f"SendInstance {send_instance_id} not found"
        )

    if send_instance.status in ("sending", "sent"):
        raise ValueError(
            f"SendInstance {send_instance_id} is already {send_instance.status} — refusing to send again"
        )

    send_instance.status = "sending"
    db.commit()

    # "rerun" audiences are re-resolved against the group right now, just before
    # sending, so a send reflects who matches at send time — not who matched when
    # it was planned. "freeze" sends keep their planned executions untouched.
    if send_instance.audience_resolution_mode == "rerun":
        try:
            reconcile_executions_to_audience(db, send_instance)
        except ValueError:
            send_instance.status = "failed"
            db.commit()
            raise

    snapshot = (
        db.query(SnapshotDB)
        .filter(
            SnapshotDB.id == send_instance.snapshot_id
        )
        .first()
    )

    if snapshot is None:
        raise ValueError(
            f"Snapshot {send_instance.snapshot_id} not found"
        )

    # Subject line comes from the variant (recipient-facing copy), not the
    # send_instance.name (an internal label). Fall back to the send_instance
    # name only if the variant has no subject set, so older data still sends.
    variant = (
        db.query(VariantDB)
        .filter(VariantDB.id == snapshot.variant_id)
        .first()
    )
    subject = (variant.subject if variant and variant.subject else send_instance.name)

    provider = get_provider(
        send_instance.provider or "mock",
        from_address=send_instance.from_address,
    )

    executions = (
        db.query(DeliveryExecutionDB)
        .filter(
            DeliveryExecutionDB.send_instance_id
            == send_instance_id
        )
        .all()
    )

    try:
        for execution in executions:

            # execution.recipient_id is a direct FK to RecipientDB.id, so no
            # external_id translation is needed here (ADR-054).
            recipient = (
                db.query(RecipientDB)
                .filter(RecipientDB.id == execution.recipient_id)
                .first()
            )

            # Resolve HTML per recipient rather than reusing one shared
            # variant-level snapshot — decision-slot personalization can
            # resolve different content per recipient within the same
            # variant (ADR-083), so every recipient must get their own
            # rendered HTML, not identical copies of whatever the snapshot
            # happened to freeze for a single (or no) recipient.
            html = render_variant_html(
                db=db,
                variant_id=snapshot.variant_id,
                recipient_id=execution.recipient_id,
                mode="send",
            )

            result = provider.send(
                recipient_email=recipient.email if recipient is not None else "",
                subject=subject,
                html=html,
            )

            logger.info(
                "send result: execution_id=%s recipient_id=%s success=%s "
                "provider_message_id=%s message=%s",
                execution.id,
                execution.recipient_id,
                result.success,
                result.provider_message_id,
                result.message,
            )

            execution.status = "sent" if result.success else "failed"
            execution.provider_message_id = (
                result.provider_message_id
            )

            # Commit after each execution — if provider.send() raises mid-batch,
            # executions already sent must not lose their persisted status just
            # because a later one in the loop failed.
            db.commit()
    except Exception:
        send_instance.status = "failed"
        db.commit()
        raise

    send_instance.status = "sent"
    db.commit()