from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
from app.campaigns.models import Campaign, CampaignWithVariants, Variant, ModuleInstance, DecisionSlot, DecisionResolution


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
    campaign = CampaignDB(
        name=name,
        status=status,
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    initial_variant = VariantDB(
        campaign_id=campaign.id,
        name=initial_variant_name,
        status="draft",
    )

    db.add(initial_variant)
    db.commit()
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
    status: str = "draft",
) -> Variant:
    variant = VariantDB(
        campaign_id=campaign_id,
        name=name,
        status=status,
    )

    db.add(variant)
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
    position: int,
    content_record_id: int | None = None,
    module_data: dict | None = None,
    decision_slot_id: int | None = None,
) -> ModuleInstance:
    module = ModuleInstanceDB(
        variant_id=variant_id,
        module_type=module_type,
        position=position,
        content_record_id=content_record_id,
        decision_slot_id=decision_slot_id,
        module_data=module_data,
    )

    db.add(module)
    db.commit()
    db.refresh(module)

    return to_module_instance(module)


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
    score: int | None = None,
) -> DecisionResolution:
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


