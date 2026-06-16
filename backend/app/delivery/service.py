from sqlalchemy.orm import Session
from pathlib import Path

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.models import DeliveryExecution, SendInstance

from app.delivery.providers.factory import get_provider
from app.snapshots.db_models import SnapshotDB


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
    recipient_id: str,
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
    send_instance = (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.id == send_instance_id
        )
        .first()
    )

    if send_instance is None:
        raise ValueError(
            f"SendInstance {send_instance_id} not found"
        )

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

    html = Path(
        snapshot.html_location
    ).read_text(
        encoding="utf-8"
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

    for execution in executions:

        result = provider.send(
            recipient_id=execution.recipient_id,
            subject=send_instance.name,
            html=html,
        )

        execution.status = "sent"
        execution.provider_message_id = (
            result.provider_message_id
        )

    db.commit()