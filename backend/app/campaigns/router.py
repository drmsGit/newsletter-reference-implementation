from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.service import ensure_default_brand
from app.database import get_db
from app.campaigns.models import (
    Campaign,
    CampaignCreate,
    CampaignWithVariants,
    Variant,
    VariantCreate,
    ModuleInstance,
    ModuleInstanceCreate,
    DecisionSlot,
    DecisionSlotCreate,
    DecisionResolution,
    DecisionResolutionCreate,
)
from app.campaigns.service import (
    create_campaign,
    create_variant_for_campaign,
    list_campaigns,
    list_variants_for_campaign,
    create_module_for_variant,
    list_modules_for_variant,
    delete_module,
    move_module,
    create_decision_slot_for_variant,
    list_decision_slots_for_variant,
    create_decision_resolution,
    list_resolutions_for_decision_slot,
)



def _request_brand(request: Request, db: Session) -> int:
    """The brand this request was authorised for (ADR-168).

    `enforce_api_policy` resolves it and writes it back, so both planes arrive
    here by one path. Falls back to the default brand only when the permission
    was not brand-scoped and nothing set one.
    """
    brand = getattr(request.state, "current_brand", None)
    return brand["id"] if brand else ensure_default_brand(db).id


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=list[Campaign])
def get_campaigns(db: Session = Depends(get_db)):
    return list_campaigns(db)


@router.post("/", response_model=CampaignWithVariants)
def create_campaign_record(
    request: Request,
    payload: CampaignCreate,
    db: Session = Depends(get_db),
):
    # PROVISIONAL. This router is unauthenticated (main.py leaves the twelve
    # JSON routers unguarded — launch gate 3), so there is no session and no
    # working brand. **Resolved 2026-09-19 (ADR-168).** `enforce_api_policy`
    # now writes the brand it actually checked the permission against onto
    # `request.state.current_brand` — the declared `X-Brand` for a machine, the
    # session's working brand for a person — so this row is written to the same
    # brand the caller was authorised for. Writing to the default brand while
    # checking against a declared one was the gap: it authorised a caller for
    # brand B and then put the row in brand A.
    return create_campaign(
        db=db,
        name=payload.name,
        brand_id=_request_brand(request, db),
        # Same provisional posture as brand_id above: this router has no session
        # to read a choice from. Email is the honest default for a machine
        # caller until ADR-166's credentials arrive, and it is stated here
        # rather than defaulted in `create_campaign`, which refuses to guess.
        channel=payload.channel,
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
        channel=payload.channel,
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
    try:
        return create_module_for_variant(
            db=db,
            variant_id=variant_id,
            module_type=payload.module_type,
            content_record_id=payload.content_record_id,
            decision_slot_id=payload.decision_slot_id,
            module_data=payload.module_data,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.delete("/modules/{module_id}")
def delete_variant_module(module_id: int, db: Session = Depends(get_db)):
    if not delete_module(db, module_id):
        raise HTTPException(status_code=404, detail="Module not found")
    return {"status": "deleted", "module_id": module_id}


@router.post("/modules/{module_id}/move", response_model=ModuleInstance)
def move_variant_module(
    module_id: int,
    direction: str,
    db: Session = Depends(get_db),
):
    """Move a module one step 'up' or 'down' within its variant."""
    try:
        result = move_module(db, module_id, direction)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return result


@router.get("/variants/{variant_id}/decision-slots", response_model=list[DecisionSlot])
def get_variant_decision_slots(
    variant_id: int,
    db: Session = Depends(get_db),
):
    return list_decision_slots_for_variant(
        db=db,
        variant_id=variant_id,
    )


@router.post("/variants/{variant_id}/decision-slots", response_model=DecisionSlot)
def create_variant_decision_slot(
    variant_id: int,
    payload: DecisionSlotCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_decision_slot_for_variant(
            db=db,
            variant_id=variant_id,
            name=payload.name,
            decision_type=payload.decision_type,
            decision_strategy=payload.decision_strategy,
            candidate_filter=payload.candidate_filter,
            strategy_config=payload.strategy_config,
            max_results=payload.max_results,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/decision-slots/{decision_slot_id}/resolutions", response_model=list[DecisionResolution])
def get_decision_slot_resolutions(
    decision_slot_id: int,
    db: Session = Depends(get_db),
):
    return list_resolutions_for_decision_slot(
        db=db,
        decision_slot_id=decision_slot_id,
    )


@router.post("/decision-slots/{decision_slot_id}/resolutions", response_model=DecisionResolution)
def create_decision_slot_resolution(
    decision_slot_id: int,
    payload: DecisionResolutionCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_decision_resolution(
            db=db,
            decision_slot_id=decision_slot_id,
            content_record_id=payload.content_record_id,
            reason=payload.reason,
            score=payload.score,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))