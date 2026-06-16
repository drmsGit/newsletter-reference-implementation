from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.campaigns.models import DecisionResolution
from app.decision.strategies.registry import get_strategy


def execute_decision_slot(
    db: Session,
    decision_slot_id: int,
) -> DecisionResolution:
    slot = (
        db.query(DecisionSlotDB)
        .filter(DecisionSlotDB.id == decision_slot_id)
        .first()
    )

    if slot is None:
        raise ValueError(f"DecisionSlot {decision_slot_id} not found")

    strategy = get_strategy(slot.decision_strategy)

    return strategy.execute(
        db=db,
        slot=slot,
    )