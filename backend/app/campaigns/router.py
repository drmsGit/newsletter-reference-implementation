from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.campaigns.models import (
    Campaign,
    CampaignCreate,
    CampaignWithVariants,
    Variant,
    VariantCreate,
)
from app.campaigns.service import (
    create_campaign,
    create_variant_for_campaign,
    list_campaigns,
    list_variants_for_campaign,
)


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=list[Campaign])
def get_campaigns(db: Session = Depends(get_db)):
    return list_campaigns(db)


@router.post("/", response_model=CampaignWithVariants)
def create_campaign_record(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
):
    return create_campaign(
        db=db,
        name=payload.name,
        status=payload.status,
        initial_variant_name=payload.initial_variant_name,
    )


@router.get("/{campaign_id}/variants", response_model=list[Variant])
def get_campaign_variants(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    return list_variants_for_campaign(
        db=db,
        campaign_id=campaign_id,
    )


@router.post("/{campaign_id}/variants", response_model=Variant)
def create_campaign_variant(
    campaign_id: int,
    payload: VariantCreate,
    db: Session = Depends(get_db),
):
    return create_variant_for_campaign(
        db=db,
        campaign_id=campaign_id,
        name=payload.name,
        status=payload.status,
    )