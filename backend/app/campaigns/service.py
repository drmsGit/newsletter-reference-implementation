from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB
from app.campaigns.models import Campaign, CampaignWithVariants, Variant


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