from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB, DecisionResolutionDB
from app.campaigns.models import DecisionResolution
from app.campaigns.service import create_decision_resolution, to_decision_resolution
from app.decision.strategies.registry import get_strategy
from app.recipients.db_models import RecipientDB
from app.recipients.service import CONSENTING_STATUS


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

    # Consent gate (belt-and-suspenders behind audience resolution): never run
    # per-recipient decisioning for a non-consenting recipient. The primary
    # gate keeps them out of the resolved audience in the first place, but a
    # decision slot can also be executed directly by recipient_id, so refuse
    # here too rather than spend AI/token budget on someone who can't be sent to.
    if recipient_id is not None:
        recipient = (
            db.query(RecipientDB).filter(RecipientDB.id == recipient_id).first()
        )
        if recipient is None:
            raise ValueError(f"Recipient {recipient_id} not found")
        if recipient.consent_status != CONSENTING_STATUS:
            raise ValueError(
                f"Recipient {recipient_id} is not opted-in "
                f"(consent_status='{recipient.consent_status}') — decisioning is "
                "gated at audience-resolution time and must not run for "
                "non-consenting recipients"
            )

    strategy = get_strategy(slot.decision_strategy)

    if strategy.meta.requires_recipient and recipient_id is None:
        raise ValueError(
            f"Strategy '{slot.decision_strategy}' requires a recipient_id"
        )

    result = strategy.execute(db=db, slot=slot, recipient_id=recipient_id)

    if result is None:
        return None

    # Non-personalized strategies (recipient_id=NULL) keep exactly one
    # resolution row per slot — a re-run always updates it in place, never
    # inserts a duplicate. Personalized strategies only get a new row when
    # the outcome actually changed since the recipient's last resolution —
    # "no new signal, keep the last recommendation" — instead of
    # accumulating an unbounded, ever-growing per-person history.
    effective_recipient_id = recipient_id if strategy.meta.requires_recipient else None
    new_score = result.score

    latest = (
        db.query(DecisionResolutionDB)
        .filter(
            DecisionResolutionDB.decision_slot_id == slot.id,
            DecisionResolutionDB.recipient_id == effective_recipient_id,
        )
        .order_by(DecisionResolutionDB.created_at.desc())
        .first()
    )

    if latest is not None and (
        latest.content_record_id == result.content_record_id
        and latest.content_version_id == result.content_version_id
        and latest.score == new_score
    ):
        return to_decision_resolution(latest)

    if not strategy.meta.requires_recipient and latest is not None:
        latest.content_record_id = result.content_record_id
        latest.content_version_id = result.content_version_id
        latest.reason = result.reason
        latest.score = new_score
        db.commit()
        db.refresh(latest)
        return to_decision_resolution(latest)

    return create_decision_resolution(
        db=db,
        decision_slot_id=slot.id,
        recipient_id=effective_recipient_id,
        content_record_id=result.content_record_id,
        content_version_id=result.content_version_id,
        reason=result.reason,
        score=new_score,
    )
