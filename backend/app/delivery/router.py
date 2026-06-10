from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.delivery.models import DeliveryExecution, DeliveryExecutionCreate
from app.delivery.service import (
    create_delivery_execution,
    list_delivery_executions_for_snapshot,
)


router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.post("/executions", response_model=DeliveryExecution)
def create_execution(
    payload: DeliveryExecutionCreate,
    db: Session = Depends(get_db),
):
    return create_delivery_execution(
        db=db,
        snapshot_id=payload.snapshot_id,
        recipient_id=payload.recipient_id,
        status=payload.status,
        provider=payload.provider,
        provider_message_id=payload.provider_message_id,
    )


@router.get("/snapshots/{snapshot_id}/executions", response_model=list[DeliveryExecution])
def get_executions_for_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
):
    return list_delivery_executions_for_snapshot(
        db=db,
        snapshot_id=snapshot_id,
    )