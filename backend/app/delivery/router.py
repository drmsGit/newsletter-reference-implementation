from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.delivery.models import (
    DeliveryExecution,
    DeliveryExecutionCreate,
    SendInstance,
    SendInstanceCreate,
)
from app.delivery.service import (
    create_delivery_execution,
    create_send_instance,
    list_delivery_executions_for_send_instance,
    list_send_instances_for_snapshot,
)


router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.post("/executions", response_model=DeliveryExecution)
def create_execution(
    payload: DeliveryExecutionCreate,
    db: Session = Depends(get_db),
):
    return create_delivery_execution(
        db=db,
        send_instance_id=payload.send_instance_id,
        recipient_id=payload.recipient_id,
        status=payload.status,
        provider=payload.provider,
        provider_message_id=payload.provider_message_id,
    )


@router.post("/send-instances", response_model=SendInstance)
def create_send_instance_record(
    payload: SendInstanceCreate,
    db: Session = Depends(get_db),
):
    return create_send_instance(
        db=db,
        snapshot_id=payload.snapshot_id,
        name=payload.name,
        status=payload.status,
        provider=payload.provider,
        scheduled_at=payload.scheduled_at,
    )


@router.get("/snapshots/{snapshot_id}/send-instances", response_model=list[SendInstance])
def get_send_instances_for_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
):
    return list_send_instances_for_snapshot(
        db=db,
        snapshot_id=snapshot_id,
    )


@router.get("/send-instances/{send_instance_id}/executions", response_model=list[DeliveryExecution])
def get_executions_for_send_instance(
    send_instance_id: int,
    db: Session = Depends(get_db),
):
    return list_delivery_executions_for_send_instance(
        db=db,
        send_instance_id=send_instance_id,
    )