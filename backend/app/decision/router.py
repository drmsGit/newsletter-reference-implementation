from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.campaigns.models import DecisionResolution
from app.database import get_db
from app.decision.service import execute_decision_slot
from app.decision.strategies.base import StrategyMeta
from app.decision.strategies.registry import list_strategies


router = APIRouter(prefix="/decision", tags=["decision"])


class DecisionExecutionRequest(BaseModel):
    recipient_id: int | None = None


@router.get("/strategies", response_model=list[StrategyMeta])
def get_strategies():
    return list_strategies()


@router.post("/slots/{decision_slot_id}/execute", response_model=DecisionResolution | None)
def execute_slot(
    decision_slot_id: int,
    payload: DecisionExecutionRequest | None = None,
    db: Session = Depends(get_db),
):
    try:
        return execute_decision_slot(
            db=db,
            decision_slot_id=decision_slot_id,
            recipient_id=payload.recipient_id if payload else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
