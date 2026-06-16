from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.campaigns.models import DecisionResolution
from app.database import get_db
from app.decision.service import execute_decision_slot


router = APIRouter(prefix="/decision", tags=["decision"])


@router.post("/slots/{decision_slot_id}/execute", response_model=DecisionResolution)
def execute_slot(
    decision_slot_id: int,
    db: Session = Depends(get_db),
):
    try:
        return execute_decision_slot(
            db=db,
            decision_slot_id=decision_slot_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )