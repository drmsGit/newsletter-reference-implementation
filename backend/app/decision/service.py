import uuid

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB, DecisionResolutionDB, VariantDB
from app.campaigns.models import DecisionResolution
from app.campaigns.service import create_decision_resolution, to_decision_resolution
from app.decision.sets import own_set
from app.decision.strategies.base import sending_brand_id
from app.decision.strategies.registry import get_strategy
from app.recipients.db_models import RecipientDB
from app.recipients.consent import MARKETING, require_consent


def execute_decision_slot(
    db: Session,
    decision_slot_id: int,
    recipient_id: int | None = None,
    *,
    brand_id: int | None = None,
    exclude: frozenset[int] = frozenset(),
) -> DecisionResolution | None:
    """Resolve the slot for a recipient and store its ranked set of picks —
    up to the slot's "show up to" (ADR-084 addendum 2026-10-11, task-109).
    Returns the first pick, or None when nothing was found; the whole set is
    read through `app.decision.sets`.

    `exclude`: records an earlier slot in the same email already shows to
    this recipient, which this slot passes over for its next candidates.
    """
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
        # On the slot's own channel (task-321): consent is per channel and
        # purpose (ADR-163), and the default here is email — so a push slot
        # refused push-only consent and accepted email-only consent.
        channel = db.query(VariantDB.channel).filter(VariantDB.id == slot.variant_id).scalar()
        require_consent(db, recipient_id, sending_brand_id(db, slot), channel=channel, purpose=MARKETING)

    strategy = get_strategy(slot.decision_strategy)

    if strategy.meta.requires_recipient and recipient_id is None:
        raise ValueError(
            f"Strategy '{slot.decision_strategy}' requires a recipient_id"
        )

    limit = min(max(slot.max_results or 1, 1), 5)
    if strategy.meta.requires_recipient:
        return _store(db, slot, recipient_id,
                      strategy.rank(db, slot, recipient_id, limit=limit, exclude=exclude))

    # A global slot keeps one set for everyone, stored as always. Only when an
    # earlier slot in this email already shows one of its picks does this
    # recipient get a set of their own, re-ranked without those records; once
    # that stops being so, the own set goes, so it can never hide the current
    # global one (ADR-084 addendum 2026-10-11, point 4).
    results = strategy.rank(db, slot, None, limit=limit)
    head = _store(db, slot, None, results)
    if recipient_id is None:
        return head
    if exclude & {r.content_record_id for r in results}:
        return _store(db, slot, recipient_id, strategy.rank(db, slot, None, limit=limit, exclude=exclude))
    db.query(DecisionResolutionDB).filter(
        DecisionResolutionDB.decision_slot_id == slot.id,
        DecisionResolutionDB.recipient_id == recipient_id,
    ).delete(synchronize_session=False)
    db.commit()
    return head


def _store(db: Session, slot: DecisionSlotDB, owner: int | None, results: list) -> DecisionResolution | None:
    """Keep `results` as the slot's set for `owner` (None: the global set)
    and return its first pick, or None when there are none.

    A personalised set only gets new rows when the outcome changed since the
    owner's last one — "no new signal, keep the last recommendation" —
    instead of an ever-growing per-person history. The global set is updated
    in place, never duplicated."""
    if not results:
        return None
    current = own_set(db, slot.id, owner)

    def shape(rows):
        return [(r.content_record_id, r.content_version_id, r.score) for r in rows]

    if current and shape(current) == shape(results):
        return to_decision_resolution(current[0])

    # **Resolved from the slot, not from a caller.** Executing a slot happens
    # at send time and from the UI, neither of which should be able to tell a
    # resolution which brand it belongs to — the slot's own campaign already
    # knows (ADR-172 point 5's resolver half).
    from app.campaigns.service import brand_of_variant

    if owner is None and current:
        pick_set = current[0].pick_set or uuid.uuid4().hex
        for rank, result in enumerate(results, start=1):
            if rank <= len(current):
                row = current[rank - 1]
                row.content_record_id = result.content_record_id
                row.content_version_id = result.content_version_id
                row.reason = result.reason
                row.score = result.score
                row.rank, row.pick_set = rank, pick_set
            else:
                db.add(DecisionResolutionDB(
                    decision_slot_id=slot.id, recipient_id=None, content_record_id=result.content_record_id,
                    content_version_id=result.content_version_id, reason=result.reason, score=result.score,
                    rank=rank, pick_set=pick_set,
                ))
        for surplus in current[len(results):]:
            db.delete(surplus)
        db.commit()
        db.refresh(current[0])
        return to_decision_resolution(current[0])

    pick_set = uuid.uuid4().hex
    brand = brand_of_variant(db, slot.variant_id)
    made = [
        create_decision_resolution(
            db=db,
            brand_id=brand,
            decision_slot_id=slot.id,
            recipient_id=owner,
            content_record_id=result.content_record_id,
            content_version_id=result.content_version_id,
            reason=result.reason,
            score=result.score,
            rank=rank,
            pick_set=pick_set,
            commit=False,
        )
        for rank, result in enumerate(results, start=1)
    ]
    db.commit()
    return made[0]
