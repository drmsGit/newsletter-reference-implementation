from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import working_brand
from app.database import get_db
from app.campaigns.models import (
    Campaign,
    CampaignCreate,
    CampaignWithVariants,
    Variant,
    VariantCreate,
    VariantUpdate,
    ModuleInstance,
    ModuleInstanceCreate,
    ModuleInstanceUpdate,
    DecisionSlot,
    DecisionSlotCreate,
    DecisionResolution,
    DecisionResolutionCreate,
    DecisionSlotUpdate,
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
    update_variant,
    update_module,
    update_decision_slot,
    to_decision_slot
)



router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=list[Campaign])
def get_campaigns(db: Session = Depends(get_db)):
    return list_campaigns(db)


@router.post("/", response_model=CampaignWithVariants)
def create_campaign_record(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
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
        brand_id=brand_id,
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


# --- editing (ADR-002) -----------------------------------------------------
#
# Added 2026-09-19. A variant, a module and a decision slot could each be
# CREATED and DELETED over JSON and not edited, which made the campaign builder
# — the first screen of the React MVP — impossible to build against the API.
# The UI has had all three since the Jinja build; this closes the half of
# ADR-002 that had quietly drifted.

@router.put("/variants/{variant_id}", response_model=Variant)
def update_variant_record(
    variant_id: int,
    payload: VariantUpdate,
    db: Session = Depends(get_db),
):
    """Rename a variant and set its envelope copy.

    `subject` and `preheader` are **not columns** — ADR-162 point 1 made them
    fields of a `header` module and migration 0012 dropped them. `update_variant`
    writes them through `set_envelope_fields`, so a channel that declares no
    envelope simply has nowhere to put them and they are ignored rather than
    refused.
    """
    updated = update_variant(
        db,
        variant_id=variant_id,
        name=payload.name,
        subject=payload.subject,
        preheader=payload.preheader,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    return updated


@router.put("/modules/{module_id}", response_model=ModuleInstance)
def update_module_record(
    module_id: int,
    payload: ModuleInstanceUpdate,
    db: Session = Depends(get_db),
):
    """Edit a module's type, source and static data.

    Position is not here: reordering moves through `/modules/{id}/move`,
    because it is a different act and carries the `(variant_id, position)`
    uniqueness constraint that a plain update would have to reason about.

    The content-or-slot exclusivity is enforced by a CHECK constraint rather
    than by this route, so a payload naming both is refused by the database —
    which is where that rule belongs, since rendering silently prefers the
    content record and ignores the slot.
    """
    try:
        updated = update_module(
            db,
            module_id=module_id,
            module_type=payload.module_type,
            content_record_id=payload.content_record_id,
            module_data=payload.module_data,
            decision_slot_id=payload.decision_slot_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if updated is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return updated


@router.put("/decision-slots/{slot_id}", response_model=DecisionSlot)
def update_decision_slot_record(
    slot_id: int,
    payload: DecisionSlotUpdate,
    db: Session = Depends(get_db),
):
    """Change a slot's strategy and its configuration.

    The strategy name is validated against the registry rather than stored on
    trust: an unknown strategy resolves nothing at send time and reports it as
    graceful degradation (ADR-086), which is the right answer for a strategy
    that found no candidates and the wrong one for a typo.
    """
    from app.decision.strategies.registry import get_strategy

    try:
        # `get_strategy` RAISES on an unknown name rather than returning None —
        # checked against the source rather than assumed, after assuming wrong
        # once and turning a 400 into a 500.
        get_strategy(payload.decision_strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{payload.decision_strategy}' is not a registered decision "
                "strategy"
            ),
        )
    updated = update_decision_slot(
        db,
        slot_id=slot_id,
        decision_strategy=payload.decision_strategy,
        candidate_filter=payload.candidate_filter,
        strategy_config=payload.strategy_config,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Decision slot not found")
    return to_decision_slot(updated)
