from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
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
    send_send_instance,
)


router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.post(
    "/executions",
    response_model=DeliveryExecution,
    summary="Create a delivery execution",
    description=(
        "Low-level: create one per-recipient delivery execution against an existing "
        "send instance. Most sends materialize executions in bulk via the audience "
        "plan flow (UI `POST /ui/campaigns/{id}/snapshots/{sid}/send-instances`); "
        "use this only for ad-hoc/manual rows."
    ),
)
def create_execution(
    payload: DeliveryExecutionCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_delivery_execution(
            db=db,
            send_instance_id=payload.send_instance_id,
            recipient_id=payload.recipient_id,
            status=payload.status,
            provider=payload.provider,
            provider_message_id=payload.provider_message_id,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"send_instance_id={payload.send_instance_id} or recipient_id={payload.recipient_id} does not exist",
        )


@router.post(
    "/send-instances",
    response_model=SendInstance,
    summary="Create a send instance",
    description=(
        "Create a send instance bound to a snapshot. This creates the record only; "
        "it does not resolve an audience or send. See the delivery module page for "
        "the full plan → fire flow."
    ),
)
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


@router.get(
    "/snapshots/{snapshot_id}/send-instances",
    response_model=list[SendInstance],
    summary="List sends for a snapshot",
)
def get_send_instances_for_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
):
    return list_send_instances_for_snapshot(
        db=db,
        snapshot_id=snapshot_id,
    )


@router.get(
    "/send-instances/{send_instance_id}/executions",
    response_model=list[DeliveryExecution],
    summary="List executions for a send",
)
def get_executions_for_send_instance(
    send_instance_id: int,
    db: Session = Depends(get_db),
):
    return list_delivery_executions_for_send_instance(
        db=db,
        send_instance_id=send_instance_id,
    )


@router.post(
    "/send-instances/{send_instance_id}/send",
    summary="Fire a send instance",
    description=(
        "Run the send loop for a planned send: per recipient, resolve their decision "
        "content, render their HTML, hand it to the provider, and record the outcome. "
        "One-shot (row-locked) — a send already sending/sent is refused with 409."
    ),
    responses={
        200: {
            "description": "The send completed.",
            "content": {"application/json": {"example": {"status": "sent"}}},
        },
        409: {
            "description": "Already sending/sent, or a rerun audience exceeded the send cap.",
            "content": {
                "application/json": {
                    "example": {"detail": "SendInstance 12 is already sent — refusing to send again"}
                }
            },
        },
    },
)
def send_instance(
    send_instance_id: int,
    db: Session = Depends(get_db),
):
    try:
        send_send_instance(
            db=db,
            send_instance_id=send_instance_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

    return {
        "status": "sent"
    }