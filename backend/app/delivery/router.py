from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import working_brand
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db
from app.delivery.models import (
    TestSendRequest,
    TestSendResponse,
    ProcessDueResult,
    DeliveryExecution,
    DeliveryExecutionCreate,
    SendInstance,
    SendInstanceCreate,
    SendInstanceDetail,
    SendPlanRequest,
    DeliveryAsSent,
    ExecutionTrace,
    SendInstanceListed,
)
from app.delivery.service import (
    send_test_email,
    create_delivery_execution,
    create_send_instance,
    list_delivery_executions_for_send_instance,
    list_send_instances,
    list_send_instances_for_snapshot,
    send_instance_detail,
    send_send_instance,
    NotInBrand,
    prepare_send_from_audience,
    reconstruct_delivery,
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


@router.post(
    "/snapshots/{snapshot_id}/send-instances",
    response_model=SendInstance,
    status_code=201,
    summary="Plan a send: resolve an audience into a send and its executions",
    description=(
        "The JSON twin of the UI plan form. Resolves the audience group to its "
        "consenting recipients now and creates the send (`draft`, or `scheduled` "
        "when `scheduled_at` is given) with one execution per recipient. "
        "Nothing is sent; fire it with `POST /delivery/send-instances/{id}/send`. "
        "Refused with 409 when the audience resolves to nobody or to more than "
        "the send cap, or the provider cannot carry the variant's channel; 404 "
        "when the snapshot or audience is not in the working brand. "
        "**Not idempotent:** a retried request plans a second send."
    ),
)
def plan_send(
    snapshot_id: int,
    payload: SendPlanRequest,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        return prepare_send_from_audience(
            db,
            snapshot_id=snapshot_id,
            name=payload.name,
            audience_group_id=payload.audience_group_id,
            provider=payload.provider,
            from_address=(payload.from_address or "").strip() or None,
            scheduled_at=payload.scheduled_at,
            brand_id=brand_id,
        )
    except NotInBrand as error:
        # Another brand's row and a missing one answer alike (ADR-172 point 6).
        raise HTTPException(status_code=404, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get(
    "/send-instances",
    response_model=Page[SendInstanceListed],
    summary="List sends in the working brand, newest first",
)
def get_send_instances(
    params: PageParams = Depends(page_params),
    status: str | None = None,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """The deliveries list (task-28): what has been sent, across campaigns.

    Answers *what did this send do* — send-level. Where campaigns stand,
    including ones that have sent nothing, is the separate monitoring screen
    (task-216); one screen answering both would answer neither well.
    """
    return list_send_instances(
        db, brand_id=brand_id, limit=params.limit, offset=params.offset, status=status)


@router.get(
    "/send-instances/{send_instance_id}",
    response_model=SendInstanceDetail,
    summary="One send, with what explains its sent/failed/excluded gap",
)
def get_send_instance_detail(
    send_instance_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    detail = send_instance_detail(db, send_instance_id, brand_id=brand_id)
    if detail is None:
        # Another brand's send and a missing one answer the same.
        raise HTTPException(status_code=404, detail=f"SendInstance {send_instance_id} not found")
    return detail


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
    response_model=Page[DeliveryExecution],
    summary="List executions for a send",
)
def get_executions_for_send_instance(
    send_instance_id: int,
    q: str | None = Query(None, description="Find recipients by identifier or address (part, any case)."),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.delivery.service import page_delivery_executions_for_send_instance

    return page_delivery_executions_for_send_instance(
        db, send_instance_id, params, brand_id=brand_id, q=q)


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
    response_model=TestSendResponse,
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


@router.post("/process-due", response_model=ProcessDueResult)
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


@router.get(
    "/executions/{execution_id}/as-sent",
    response_model=DeliveryAsSent,
    summary="What this recipient got, as of the send date",
    description=(
        "Rebuilt from the snapshot's frame and the execution's delivery record "
        "(ADR-183): every value is the one that was sent — content versions, "
        "static fields, overrides, this recipient's slot picks, the subject. "
        "The layout is today's templates: `templates_match` says whether they "
        "are the ones used, `hash_matches` whether the output is byte-identical. "
        "404 when the execution is not in the working brand; 409 when it was not "
        "sent, or was sent before delivery records existed."
    ),
)
def get_delivery_as_sent(
    execution_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        result = reconstruct_delivery(db, execution_id, brand_id=brand_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    return result


@router.get(
    "/executions/{execution_id}/trace",
    response_model=ExecutionTrace,
    summary="One execution's engagement events and what each taught the profile",
    description=(
        "Each event newest first, with the signal contributions it produced "
        "(category, weight, type). An event that named no content produced none "
        "(ADR-182). 404 when the execution is not in the working brand."
    ),
)
def get_execution_trace(
    execution_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.insight.service import event_trace

    found = (
        db.query(DeliveryExecutionDB.id)
        .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
        .filter(DeliveryExecutionDB.id == execution_id, SendInstanceDB.brand_id == brand_id)
        .first()
    )
    if found is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    return {"execution_id": execution_id,
            "events": event_trace(db, [execution_id], brand_id=brand_id).get(execution_id, [])}
