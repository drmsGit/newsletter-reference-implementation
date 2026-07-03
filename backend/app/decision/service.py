from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.campaigns.models import DecisionResolution
from app.campaigns.service import create_decision_resolution
from app.decision.strategies.registry import get_strategy


def execute_decision_slot(
    db: Session,
    decision_slot_id: int,
    recipient_id: int | None = None,
) -> DecisionResolution | None:
    slot = (
        db.query(DecisionSlotDB)
        .filter(DecisionSlotDB.id == decision_slot_id)
        .first()
    )

    if slot is None:
        raise ValueError(f"DecisionSlot {decision_slot_id} not found")

    strategy = get_strategy(slot.decision_strategy)

    if strategy.meta.requires_recipient and recipient_id is None:
        raise ValueError(
            f"Strategy '{slot.decision_strategy}' requires a recipient_id"
        )

    result = strategy.execute(db=db, slot=slot, recipient_id=recipient_id)

    if result is None:
        return None

    return create_decision_resolution(
        db=db,
        decision_slot_id=slot.id,
        recipient_id=recipient_id,
        content_record_id=result.content_record_id,
        content_version_id=result.content_version_id,
        reason=result.reason,
        score=int(result.score),
    )
