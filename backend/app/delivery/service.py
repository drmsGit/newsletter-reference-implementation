import logging

from sqlalchemy.orm import Session

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.models import DeliveryExecution, SendInstance

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
) -> SendInstance:
    send_instance = SendInstanceDB(
        snapshot_id=snapshot_id,
        name=name,
        status=status,
        provider=provider,
        scheduled_at=scheduled_at,
    )

    db.add(send_instance)
    db.commit()
    db.refresh(send_instance)

    return to_send_instance(send_instance)


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

    provider = get_provider(
        send_instance.provider or "mock"
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
                subject=send_instance.name,
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