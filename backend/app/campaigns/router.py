from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.campaigns.models import (
    Campaign,
    CampaignCreate,
    CampaignWithVariants,
    Variant,
    VariantCreate,
    ModuleInstance,
    ModuleInstanceCreate,
)
from app.campaigns.service import (
    create_campaign,
    create_variant_for_campaign,
    list_campaigns,
    list_variants_for_campaign,
    create_module_for_variant,
    list_modules_for_variant,
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


@router.get("/variants/{variant_id}/modules", response_model=list[ModuleInstance])
def get_variant_modules(
    variant_id: int,
    db: Session = Depends(get_db),
):
    return list_modules_for_variant(
        db=db,
        variant_id=variant_id,
    )


@router.post("/variants/{variant_id}/modules", response_model=ModuleInstance)
def create_variant_module(
    variant_id: int,
    payload: ModuleInstanceCreate,
    db: Session = Depends(get_db),
):
    return create_module_for_variant(
        db=db,
        variant_id=variant_id,
        module_type=payload.module_type,
        position=payload.position,
        content_record_id=payload.content_record_id,
        module_data=payload.module_data,
    )