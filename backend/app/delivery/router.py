from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import working_brand
from app.database import get_db
from app.delivery.models import (
    TestSendRequest,
    DeliveryExecution,
    DeliveryExecutionCreate,
    SendInstance,
    SendInstanceCreate,
)
from app.delivery.service import (
    send_test_email,
    create_delivery_execution,
    create_send_instance,
    list_delivery_executions_for_send_instance,
    list_send_instances_for_snapshot,
    send_send_instance,
    process_due_scheduled_sends
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
    brand_id: int = Depends(working_brand),
):
    try:
        return create_delivery_execution(
            db=db,
            send_instance_id=payload.send_instance_id,
            recipient_id=payload.recipient_id,
            status=payload.status,
            provider=payload.provider,
            provider_message_id=payload.provider_message_id,
            brand_id=brand_id,
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
    brand_id: int = Depends(working_brand),
):
    return create_send_instance(
        db=db,
        snapshot_id=payload.snapshot_id,
        name=payload.name,
        status=payload.status,
        provider=payload.provider,
        scheduled_at=payload.scheduled_at,
        brand_id=brand_id,
    )


@router.get(
    "/snapshots/{snapshot_id}/send-instances",
    response_model=list[SendInstance],
    summary="List sends for a snapshot",
)
def get_send_instances_for_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_send_instances_for_snapshot(
        db=db,
        snapshot_id=snapshot_id,
        brand_id=brand_id,
    )


@router.get(
    "/send-instances/{send_instance_id}/executions",
    response_model=list[DeliveryExecution],
    summary="List executions for a send",
)
def get_executions_for_send_instance(
    send_instance_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_delivery_executions_for_send_instance(
        db=db,
        send_instance_id=send_instance_id,
        brand_id=brand_id,
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
    brand_id: int = Depends(working_brand),
):
    try:
        send_send_instance(
            db=db,
            send_instance_id=send_instance_id,
            brand_id=brand_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

    return {
        "status": "sent"
    }

@router.post(
    "/send-test",
    summary="Send one real test email",
    description=(
        "Renders the chosen variant through the email path and mails it to one "
        "address. A render failure does not block the send — a plain body goes "
        "instead and `render_note` says so, because the point of this is to "
        "find out whether mail leaves the building at all."
    ),
)
def send_test(
    payload: TestSendRequest,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Priced as `sends.execute`, by its own entry in `policy.py`.

    The broad `/delivery` prefix would call this `sends.plan`. It reaches a
    real inbox through a real provider — that it goes to one typed address
    rather than to an audience makes it smaller, not different in kind.
    """
    sent = send_test_email(
        db,
        to=payload.to,
        subject=payload.subject,
        provider=payload.provider,
        brand_id=brand_id,
        variant_id=payload.variant_id,
        recipient_id=payload.recipient_id,
    )
    return {
        "success": sent.success,
        "to": sent.to,
        "provider": sent.provider,
        "provider_message_id": sent.provider_message_id,
        "message": sent.message,
        "render_note": sent.render_note,
    }


@router.post("/process-due")
def process_due(db: Session = Depends(get_db)):
    """Fire every scheduled send whose time has arrived.

    **The seam ADR-142 assumes exists.** That record has the orchestrator
    driving the platform's actions over the documented REST API — and this
    operation, the one a real deployment points cron at, was reachable only
    from a button in the Jinja UI. An adopter running n8n had no way to call
    the thing the architecture says they should be calling.

    `sends.execute` rather than `sends.plan`, because people receive mail
    because of this request. That is the line ADR-166 point 2 drew when it
    split the two, and a scheduler is exactly the caller the split was for: it
    prepares nothing and fires everything that is due.

    Idempotent by the send path rather than by this route —
    `send_send_instance` takes a row lock and refuses an instance already
    `sending` or `sent`, so two schedulers overlapping cannot double-send.
    """
    triggered = process_due_scheduled_sends(db)
    return {
        "triggered": len(triggered),
        "send_instance_ids": [getattr(s, "id", s) for s in triggered],
    }
