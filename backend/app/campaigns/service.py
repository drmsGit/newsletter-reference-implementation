from sqlalchemy import func
from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
from app.campaigns.models import Campaign, CampaignWithVariants, Variant, ModuleInstance, DecisionSlot, DecisionResolution
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.recipients.db_models import RecipientDB


def to_campaign(record: CampaignDB) -> Campaign:
    return Campaign(
        id=record.id,
        name=record.name,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def to_variant(record: VariantDB) -> Variant:
    return Variant(
        id=record.id,
        campaign_id=record.campaign_id,
        name=record.name,
        subject=record.subject,
        preheader=record.preheader,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_campaigns(db: Session) -> list[Campaign]:
    records = db.query(CampaignDB).all()
    return [to_campaign(record) for record in records]


def create_campaign(
    db: Session,
    name: str,
    status: str = "draft",
    initial_variant_name: str = "Variant A",
) -> CampaignWithVariants:
    # A campaign must always have a variant (invariant) — flush (not commit)
    # after the campaign insert so campaign.id is assigned without ending
    # the transaction, then commit both inserts atomically in one go. A
    # failure between them can no longer leave a persisted campaign with
    # zero variants.
    campaign = CampaignDB(
        name=name,
        status=status,
    )

    db.add(campaign)
    db.flush()

    initial_variant = VariantDB(
        campaign_id=campaign.id,
        name=initial_variant_name,
        status="draft",
    )

    db.add(initial_variant)
    db.commit()
    db.refresh(campaign)
    db.refresh(initial_variant)

    return CampaignWithVariants(
        **to_campaign(campaign).model_dump(),
        variants=[to_variant(initial_variant)],
    )


def list_variants_for_campaign(
    db: Session,
    campaign_id: int,
) -> list[Variant]:
    records = (
        db.query(VariantDB)
        .filter(VariantDB.campaign_id == campaign_id)
        .all()
    )

    return [to_variant(record) for record in records]


def create_variant_for_campaign(
    db: Session,
    campaign_id: int,
    name: str,
    subject: str | None = None,
    preheader: str | None = None,
    status: str = "draft",
) -> Variant:
    variant = VariantDB(
        campaign_id=campaign_id,
        name=name,
        subject=subject,
        preheader=preheader,
        status=status,
    )

    db.add(variant)
    db.commit()
    db.refresh(variant)

    return to_variant(variant)


def update_variant(
    db: Session,
    variant_id: int,
    name: str,
    subject: str | None = None,
    preheader: str | None = None,
) -> Variant | None:
    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    if variant is None:
        return None
    variant.name = name
    variant.subject = subject
    variant.preheader = preheader
    db.commit()
    db.refresh(variant)
    return to_variant(variant)


def to_module_instance(record: ModuleInstanceDB) -> ModuleInstance:
    return ModuleInstance(
        id=record.id,
        variant_id=record.variant_id,
        module_type=record.module_type,
        position=record.position,
        content_record_id=record.content_record_id,
        module_data=record.module_data,
        decision_slot_id=record.decision_slot_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_modules_for_variant(
    db: Session,
    variant_id: int,
) -> list[ModuleInstance]:
    records = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    return [to_module_instance(record) for record in records]


def create_module_for_variant(
    db: Session,
    variant_id: int,
    module_type: str,
    content_record_id: int | None = None,
    module_data: dict | None = None,
    decision_slot_id: int | None = None,
) -> ModuleInstance:
    if content_record_id is not None and decision_slot_id is not None:
        raise ValueError(
            "A module cannot have both content_record_id and decision_slot_id set — "
            "rendering would silently prefer content_record_id and ignore the decision slot"
        )

    max_position = (
        db.query(func.max(ModuleInstanceDB.position))
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .scalar()
    )
    next_position = (max_position or 0) + 1

    module = ModuleInstanceDB(
        variant_id=variant_id,
        module_type=module_type,
        position=next_position,
        content_record_id=content_record_id,
        decision_slot_id=decision_slot_id,
        module_data=module_data,
    )

    db.add(module)
    db.commit()
    db.refresh(module)

    return to_module_instance(module)


def _normalize_for_strategy(
    decision_strategy: str,
    candidate_filter: dict | None,
    strategy_config: dict | None,
) -> tuple[dict | None, dict | None]:
    """Resolve the strategy and lock the config/filter to its declared shape.
    Lazy imports keep the decision-strategy registry out of this module's
    import graph. Raises ValueError for an unknown strategy or a config that
    doesn't match the strategy's declared fields."""
    from app.decision.strategies.base import normalize_slot_config
    from app.decision.strategies.registry import get_strategy

    strategy = get_strategy(decision_strategy)
    return normalize_slot_config(strategy.meta, candidate_filter, strategy_config)


def update_decision_slot(
    db: Session,
    slot_id: int,
    decision_strategy: str,
    candidate_filter: dict | None,
    strategy_config: dict | None,
) -> DecisionSlotDB | None:
    slot = db.query(DecisionSlotDB).filter(DecisionSlotDB.id == slot_id).first()
    if slot is None:
        return None
    # Lock the config/filter structure to the (possibly newly-chosen) strategy
    # before persisting — no more "accepts any shape for any strategy, only
    # fails at resolution time". Switching strategies re-derives the structure.
    candidate_filter, strategy_config = _normalize_for_strategy(
        decision_strategy, candidate_filter, strategy_config
    )
    slot.decision_strategy = decision_strategy
    slot.candidate_filter = candidate_filter
    slot.strategy_config = strategy_config
    db.commit()
    db.refresh(slot)
    return slot


def to_decision_slot(record: DecisionSlotDB) -> DecisionSlot:
    return DecisionSlot(
        id=record.id,
        variant_id=record.variant_id,
        name=record.name,
        decision_type=record.decision_type,
        decision_strategy=record.decision_strategy,
        candidate_filter=record.candidate_filter,
        strategy_config=record.strategy_config,
        max_results=record.max_results,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_decision_slots_for_variant(
    db: Session,
    variant_id: int,
) -> list[DecisionSlot]:
    records = (
        db.query(DecisionSlotDB)
        .filter(DecisionSlotDB.variant_id == variant_id)
        .all()
    )

    return [to_decision_slot(record) for record in records]


def create_decision_slot_for_variant(
    db: Session,
    variant_id: int,
    name: str,
    decision_type: str = "content_recommendation",
    decision_strategy: str = "top_score",
    candidate_filter: dict | None = None,
    strategy_config: dict | None = None,
    max_results: int = 1,
) -> DecisionSlot:
    candidate_filter, strategy_config = _normalize_for_strategy(
        decision_strategy, candidate_filter, strategy_config
    )
    slot = DecisionSlotDB(
        variant_id=variant_id,
        name=name,
        decision_type=decision_type,
        decision_strategy=decision_strategy,
        candidate_filter=candidate_filter,
        strategy_config=strategy_config,
        max_results=max_results,
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)

    return to_decision_slot(slot)


def to_decision_resolution(record: DecisionResolutionDB) -> DecisionResolution:
    return DecisionResolution(
        id=record.id,
        decision_slot_id=record.decision_slot_id,
        recipient_id=record.recipient_id,
        content_record_id=record.content_record_id,
        content_version_id=record.content_version_id,
        reason=record.reason,
        score=record.score,
        created_at=record.created_at,
    )


def create_decision_resolution(
    db: Session,
    decision_slot_id: int,
    content_record_id: int,
    content_version_id: int | None = None,
    recipient_id: int | None = None,
    reason: str | None = None,
    score: float | None = None,
) -> DecisionResolution:
    # No orphan row should ever be silently accepted, regardless of whether
    # the DB engine happens to enforce FK constraints — validate referenced
    # IDs exist before insert rather than only failing later at rendering's
    # join-based lookup.
    if db.query(DecisionSlotDB.id).filter(DecisionSlotDB.id == decision_slot_id).first() is None:
        raise ValueError(f"DecisionSlot {decision_slot_id} not found")

    if db.query(ContentRecordDB.id).filter(ContentRecordDB.id == content_record_id).first() is None:
        raise ValueError(f"ContentRecord {content_record_id} not found")

    if content_version_id is not None:
        if db.query(ContentVersionDB.id).filter(ContentVersionDB.id == content_version_id).first() is None:
            raise ValueError(f"ContentVersion {content_version_id} not found")

    if recipient_id is not None:
        if db.query(RecipientDB.id).filter(RecipientDB.id == recipient_id).first() is None:
            raise ValueError(f"Recipient {recipient_id} not found")

    resolution = DecisionResolutionDB(
        decision_slot_id=decision_slot_id,
        recipient_id=recipient_id,
        content_record_id=content_record_id,
        content_version_id=content_version_id,
        reason=reason,
        score=score,
    )

    db.add(resolution)
    db.commit()
    db.refresh(resolution)

    return to_decision_resolution(resolution)


def list_resolutions_for_decision_slot(
    db: Session,
    decision_slot_id: int,
) -> list[DecisionResolution]:
    records = (
        db.query(DecisionResolutionDB)
        .filter(DecisionResolutionDB.decision_slot_id == decision_slot_id)
        .all()
    )

    return [to_decision_resolution(record) for record in records]


