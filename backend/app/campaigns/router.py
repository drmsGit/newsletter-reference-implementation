from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.campaigns.models import Campaign, CampaignCreate
from app.campaigns.service import create_campaign, list_campaigns


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=list[Campaign])
def get_campaigns(db: Session = Depends(get_db)):
    return list_campaigns(db)


@router.post("/", response_model=Campaign)
def create_campaign_record(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
):
    return create_campaign(
        db=db,
        name=payload.name,
        status=payload.status,
    )