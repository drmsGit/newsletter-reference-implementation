from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB, DecisionResolutionDB
from app.campaigns.models import DecisionResolution
from app.campaigns.service import create_decision_resolution, to_decision_resolution
from app.decision.strategies.base import sending_brand_id
from app.decision.strategies.registry import get_strategy
from app.recipients.db_models import RecipientDB
from app.recipients.consent import require_consent


def execute_decision_slot(
    db: Session,
    decision_slot_id: int,
    recipient_id: int | None = None,
    *,
    brand_id: int | None = None,
) -> DecisionResolution | None:
    # **Optional here and required by the route**, the same split rendering
    # takes. A request resolving a slot must not reach another brand's; the
    # send path already holds the brand it locked and would only be
    # re-deriving it. `Depends(working_brand)` means the route cannot forget.
    from app.campaigns.service import get_decision_slot

    slot = (
        get_decision_slot(db, decision_slot_id, brand_id=brand_id)
        if brand_id is not None
        else db.query(DecisionSlotDB)
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
        # Raises ConsentDenied — a ValueError subclass, so existing callers that
        # catch ValueError are unaffected, while a caller that needs to tell a
        # compliance refusal apart from "the strategy resolved nothing" now can.
        # That conflation is the root of the open P0 (ADR-163 point 8).
        require_consent(db, recipient_id, sending_brand_id(db, slot))

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

    # **Resolved from the slot, not from a caller.** Executing a slot happens
    # at send time and from the UI, neither of which should be able to tell a
    # resolution which brand it belongs to — the slot's own campaign already
    # knows (ADR-172 point 5's resolver half).
    from app.campaigns.service import brand_of_variant

    return create_decision_resolution(
        db=db,
        brand_id=brand_of_variant(db, slot.variant_id),
        decision_slot_id=slot.id,
        recipient_id=effective_recipient_id,
        content_record_id=result.content_record_id,
        content_version_id=result.content_version_id,
        reason=result.reason,
        score=new_score,
    )
