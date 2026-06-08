from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB
from app.campaigns.models import Campaign


def list_campaigns(db: Session) -> list[Campaign]:
    records = db.query(CampaignDB).all()

    return [
        Campaign(
            id=record.id,
            name=record.name,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record in records
    ]


def create_campaign(
    db: Session,
    name: str,
    status: str = "draft",
) -> Campaign:
    campaign = CampaignDB(
        name=name,
        status=status,
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return Campaign(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )