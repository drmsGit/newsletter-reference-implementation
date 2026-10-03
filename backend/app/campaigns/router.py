from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.auth.permissions import CAMPAIGNS_MANAGE
from app.auth.dependencies import auth_is_enforced, request_principal, working_brand
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db
from app.campaigns import duplication
from app.campaigns.db_models import CampaignDB
from app.campaigns.models import (
    Campaign,
    CampaignDuplicate,
    CampaignDuplicated,
    MonitoredCampaign,
    VariantDuplicate,
    VariantDuplicated,
    DuplicationOptions,
    DuplicationTarget,
    SuggestionRun,
    DecisionSlotListed,
    DecisionSlotStats,
    SlotCandidates,
    CampaignComposition,
    SubjectSuggestionResult,
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
    DecisionSlotPatch,
)
from app.campaigns.service import (
    ChannelUnavailable,
    ModuleDataInvalid,
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
    get_decision_slot,
    module_audit_detail,
    slot_audit_detail,
    to_decision_slot
)



router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _module_data_refused(error: ModuleDataInvalid) -> HTTPException:
    """A 422 in FastAPI's own validation shape, one entry per bad field
    (task-253). The client then reads a single kind of field error, whether
    pydantic or the manifest refused it, and marks each field in its form."""
    return HTTPException(status_code=422, detail=[
        {"loc": ["body", "module_data", field], "msg": message, "type": "value_error"}
        for field, message in error.errors
    ])


@router.get("/", response_model=Page[Campaign])
def get_campaigns(
    q: str | None = Query(None, description="Find by name (part, any case)."),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """One ADR-185 page of the brand's campaigns, newest first."""
    from app.campaigns.service import page_campaigns

    return page_campaigns(db, params, brand_id=brand_id, q=q)


@router.get(
    "/monitoring",
    response_model=Page[MonitoredCampaign],
    summary="Where every campaign in the brand is: in flight, in preparation, or sent",
    description=(
        "Derived from each variant's snapshots and sends, never stored (task-216). "
        "In flight: a snapshot no send has used yet, or a send planned, scheduled "
        "or sending. In flight first, then in preparation, then sent; newest first "
        "within each. Campaign-level: what a single send did is the deliveries list."
    ),
)
def get_campaign_monitoring(
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.campaigns.monitoring import campaign_monitoring

    # Assembled in Python from several queries, so paged after (ADR-185;
    # `page_of_list` says what that costs).
    return page_of_list(campaign_monitoring(db, brand_id=brand_id), params)


@router.post("/", response_model=CampaignWithVariants)
def create_campaign_record(
    payload: CampaignCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Create a campaign and its first variant.

    The channel is refused server-side when this deployment has not enabled it
    (ADR-160 point 8). That check used to exist only on the Jinja form, so this
    route happily created campaigns on switched-off channels until 2026-09-20.
    """
    # The brand is the one the guard authorised (ADR-168), and the channel is
    # refused if this deployment has not enabled it (ADR-160 point 8).
    #
    # The PROVISIONAL note that stood here is gone rather than amended: it
    # described a router with no guard and no working brand, which stopped
    # being true when gate 3 closed, and a stale caveat about authentication is
    # the kind a reader trusts.
    try:
        created = create_campaign(
            db=db,
            name=payload.name,
            brand_id=brand_id,
            channel=payload.channel,
            status=payload.status,
            initial_variant_name=payload.initial_variant_name,
        )
    except ChannelUnavailable as error:
        raise HTTPException(status_code=400, detail=str(error))
    audit.record_from_request(
        request, db, audit.CAMPAIGN_CREATED, subject_type="campaign", subject_id=created.id,
        detail={"name": created.name, "channel": payload.channel,
                "variant_ids": [v.id for v in created.variants]},
    )
    return created


@router.get("/{campaign_id}/variants", response_model=list[Variant])
def get_campaign_variants(
    campaign_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_variants_for_campaign(
        db=db,
        campaign_id=campaign_id,
        brand_id=brand_id,
    )


@router.post("/{campaign_id}/variants", response_model=Variant)
def create_campaign_variant(
    campaign_id: int,
    payload: VariantCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    # A campaign outside this brand is not found, so hanging a variant off it
    # answers as 404 rather than 500 (ADR-172 point 6). The service refuses
    # before writing — the alternative would create a row nobody can reach,
    # attached to a campaign nobody meant.
    try:
        created = create_variant_for_campaign(
            db=db,
            campaign_id=campaign_id,
            name=payload.name,
            channel=payload.channel,
            subject=payload.subject,
            preheader=payload.preheader,
            status=payload.status,
            brand_id=brand_id,
        )
    except ChannelUnavailable as error:
        # 400, not 404: the campaign is right there and the request is
        # well-formed — the channel is switched off (ADR-160 point 8).
        raise HTTPException(status_code=400, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    audit.record_from_request(
        request, db, audit.VARIANT_CREATED, subject_type="variant", subject_id=created.id,
        detail={"campaign_id": campaign_id, "name": created.name, "channel": created.channel},
    )
    return created


@router.get("/variants/{variant_id}/modules", response_model=list[ModuleInstance])
def get_variant_modules(
    variant_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_modules_for_variant(
        db=db,
        variant_id=variant_id,
        brand_id=brand_id,
    )


@router.post("/variants/{variant_id}/modules", response_model=ModuleInstance)
def create_variant_module(
    variant_id: int,
    payload: ModuleInstanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        created = create_module_for_variant(
            db=db,
            variant_id=variant_id,
            module_type=payload.module_type,
            content_record_id=payload.content_record_id,
            decision_slot_id=payload.decision_slot_id,
            module_data=payload.module_data,
            brand_id=brand_id,
        )
    except ModuleDataInvalid as error:
        raise _module_data_refused(error)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    audit.record_from_request(
        request, db, audit.MODULE_CREATED, subject_type="module", subject_id=created.id,
        detail=module_audit_detail(created),
    )
    return created


@router.delete("/modules/{module_id}")
def delete_variant_module(
    module_id: int,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    removed = delete_module(db, module_id, brand_id=brand_id)
    if removed is None:
        raise HTTPException(status_code=404, detail="Module not found")
    audit.record_from_request(
        request, db, audit.MODULE_DELETED, subject_type="module", subject_id=module_id,
        detail={"overrides_removed": removed},
    )
    return {"status": "deleted", "module_id": module_id}


@router.post("/modules/{module_id}/move", response_model=ModuleInstance)
def move_variant_module(
    module_id: int,
    direction: str,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Move a module one step 'up' or 'down' within its variant."""
    try:
        result = move_module(db, module_id, direction, brand_id=brand_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404, detail="Module not found")
    audit.record_from_request(
        request, db, audit.MODULE_MOVED, subject_type="module", subject_id=module_id,
        detail={"direction": direction, "position": result.position},
    )
    return result


@router.post(
    "/variants/{variant_id}/suggest-subject",
    response_model=SubjectSuggestionResult,
    summary="Ask the model for subject/preheader options",
    description=(
        "Runs ADR-141 §3's Mode A task. Nothing is written to the variant — AI "
        "output is a proposal until a person picks one. Refused without "
        "spending tokens when the channel has no subject line at all, or when "
        "there is no content to write one from."
    ),
)
def suggest_subject_for_variant_record(
    request: Request,
    variant_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """The JSON twin of the Jinja button (inventory B15).

    **The guards are in `app/ai/orchestration.py`, not here**, which is the
    whole point of the item: they lived in the Jinja route and nowhere else, so
    this route could not have existed without either duplicating them or
    spending tokens on requests that cannot succeed.

    Mapped to `ai.run` by its own entry in `policy.py` — the broad `/campaigns`
    prefix would otherwise call this "may restructure a campaign" rather than
    "may spend money on the model".
    """
    from app.ai.orchestration import suggest_subject_for_variant
    from app.audit.service import ACTOR_USER
    from app.auth.service import SESSION_COOKIE, user_for_token

    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    result = suggest_subject_for_variant(
        db, variant_id,
        brand_id=brand_id,
        requested_by_type=ACTOR_USER,
        requested_by_id=user.id if user else None,
    )

    if result.outcome in ("refused", "nothing_to_work_from"):
        # 409 rather than 400: the request is well-formed and the caller is
        # allowed to make it — the variant is simply not in a state where the
        # answer can exist. And no tokens were spent, which is what the caller
        # most wants to know.
        raise HTTPException(
            status_code=409,
            detail={"reason": result.outcome, "message": result.message},
        )
    return {
        "outcome": result.outcome,
        "message": result.message,
        "ai_run_id": result.run_id,
        "pending_action_id": result.pending_action_id,
    }


@router.get("/variants/{variant_id}/decision-slots", response_model=list[DecisionSlot])
def get_variant_decision_slots(
    variant_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_decision_slots_for_variant(
        db=db,
        variant_id=variant_id,
        brand_id=brand_id,
    )


@router.post("/variants/{variant_id}/decision-slots", response_model=DecisionSlot)
def create_variant_decision_slot(
    variant_id: int,
    payload: DecisionSlotCreate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        created = create_decision_slot_for_variant(
            db=db,
            variant_id=variant_id,
            name=payload.name,
            decision_type=payload.decision_type,
            decision_strategy=payload.decision_strategy,
            candidate_filter=payload.candidate_filter,
            strategy_config=payload.strategy_config,
            max_results=payload.max_results,
            brand_id=brand_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    audit.record_from_request(
        request, db, audit.DECISION_SLOT_CREATED, subject_type="decision_slot",
        subject_id=created.id, detail=slot_audit_detail(created),
    )
    return created


@router.get("/decision-slots/{decision_slot_id}/resolutions", response_model=Page[DecisionResolution])
def get_decision_slot_resolutions(
    decision_slot_id: int,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.campaigns.service import page_resolutions_for_decision_slot

    return page_resolutions_for_decision_slot(db, decision_slot_id, params, brand_id=brand_id)


@router.post("/decision-slots/{decision_slot_id}/resolutions", response_model=DecisionResolution)
def create_decision_slot_resolution(
    decision_slot_id: int,
    payload: DecisionResolutionCreate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        return create_decision_resolution(
            db=db,
            decision_slot_id=decision_slot_id,
            content_record_id=payload.content_record_id,
            reason=payload.reason,
            score=payload.score,
            brand_id=brand_id,
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
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
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
        brand_id=brand_id,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    audit.record_from_request(
        request, db, audit.VARIANT_UPDATED, subject_type="variant", subject_id=variant_id,
        detail={"name": updated.name, "subject": updated.subject, "preheader": updated.preheader},
    )
    return updated


@router.put("/modules/{module_id}", response_model=ModuleInstance)
def update_module_record(
    module_id: int,
    payload: ModuleInstanceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
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
            brand_id=brand_id,
        )
    except ModuleDataInvalid as error:
        raise _module_data_refused(error)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if updated is None:
        raise HTTPException(status_code=404, detail="Module not found")
    audit.record_from_request(
        request, db, audit.MODULE_UPDATED, subject_type="module", subject_id=module_id,
        detail=module_audit_detail(updated),
    )
    return updated


@router.put("/decision-slots/{slot_id}", response_model=DecisionSlot)
def update_decision_slot_record(
    slot_id: int,
    payload: DecisionSlotUpdate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Change a slot's strategy and its configuration. **Both are replaced.**

    That is what PUT means and it is left meaning it — but note what replacing
    `strategy_config` does: `_normalize_section` fills a declared key that is
    absent with its spec default, so a caller that sends only a candidate
    filter does not leave the config alone, it resets it. `recipient_top_score`
    has two tunable weights, and a manager's tuning is what gets reset.

    **Use `PATCH` for a partial edit.** It leaves a section the caller did not
    send exactly as stored.

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
    try:
        updated = update_decision_slot(
            db,
            slot_id=slot_id,
            decision_strategy=payload.decision_strategy,
            candidate_filter=payload.candidate_filter,
            strategy_config=payload.strategy_config,
            brand_id=brand_id,
        )
    except ValueError as error:
        # The filter or config does not match the strategy's declared shape
        # (`normalize_slot_config`). PATCH already answered 400 here; PUT
        # answered 500 (task-251).
        raise HTTPException(status_code=400, detail=str(error))
    if updated is None:
        raise HTTPException(status_code=404, detail="Decision slot not found")
    audit.record_from_request(
        request, db, audit.DECISION_SLOT_UPDATED, subject_type="decision_slot",
        subject_id=slot_id, detail=slot_audit_detail(updated),
    )
    return to_decision_slot(updated)


@router.patch("/decision-slots/{slot_id}", response_model=DecisionSlot)
def patch_decision_slot_record(
    slot_id: int,
    payload: DecisionSlotPatch,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Edit a slot, leaving untouched whatever the caller did not send.

    Added 2026-09-20 (inventory B16). The rule it protects is narrower than the
    inventory first described and is worth stating exactly: **"empty means all"
    was never at risk** — `_normalize_section` fills `category_ids` with its
    `[]` default and both strategies read `if category_ids:`, so an empty list
    and an absent key already behave identically. What was at risk is
    `strategy_config`, because absent declared keys are filled with defaults
    rather than left alone, so a partial PUT resets tuned weights.

    The Jinja form never had this problem: it round-trips both sections as
    pre-populated JSON, so everything it did not change it sent back unchanged.
    A JSON client has no such hidden state, which is precisely why the rule had
    to become explicit rather than remain a property of one form.
    """
    from app.decision.strategies.registry import get_strategy

    existing = get_decision_slot(db, slot_id, brand_id=brand_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Decision slot not found")

    strategy = (
        payload.decision_strategy
        if payload.sent("decision_strategy") and payload.decision_strategy
        else existing.decision_strategy
    )
    try:
        get_strategy(strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"'{strategy}' is not a registered decision strategy",
        )

    try:
        updated = update_decision_slot(
            db,
            slot_id=slot_id,
            decision_strategy=strategy,
            candidate_filter=(
                payload.candidate_filter if payload.sent("candidate_filter")
                else existing.candidate_filter
            ),
            strategy_config=(
                payload.strategy_config if payload.sent("strategy_config")
                else existing.strategy_config
            ),
            brand_id=brand_id,
        )
    except ValueError as error:
        # The filter or config did not match the chosen strategy's declared
        # shape. Surfaced now rather than crashing later at resolution time —
        # and note it can fire on a section the caller did not send, when the
        # strategy changed underneath it. That is the right answer: the stored
        # config is genuinely invalid for the new strategy.
        raise HTTPException(status_code=400, detail=str(error))

    if updated is None:
        raise HTTPException(status_code=404, detail="Decision slot not found")
    audit.record_from_request(
        request, db, audit.DECISION_SLOT_UPDATED, subject_type="decision_slot",
        subject_id=slot_id, detail=slot_audit_detail(updated),
    )
    return to_decision_slot(updated)


@router.get(
    "/{campaign_id}/duplicate-options",
    response_model=DuplicationOptions,
    summary="What the duplicate wizard offers this caller",
    description=(
        "The brands this caller may duplicate into (their own `campaigns.manage` "
        "grants, not the working brand's), the content modes allowed for each — "
        "`keep` and `layout` inside one brand, `copy` and `layout` across, with "
        "`copy` withheld unless the caller holds `content.manage` on the target — "
        "and what the copy will consist of. `variant_ids` narrows "
        "`selected_summary` to the variants being chosen. A client must not "
        "rebuild this: it is the boundary rule."
    ),
)
def duplicate_options(
    campaign_id: int,
    request: Request,
    variant_ids: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    campaign = (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id, CampaignDB.brand_id == brand_id)
        .first()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    principal, enforced = request_principal(request), auth_is_enforced(request)
    targets = duplication.target_brands(
        db, principal, permission=CAMPAIGNS_MANAGE, enforced=enforced)
    return DuplicationOptions(
        source_brand_id=brand_id,
        summary=duplication.summarise_source(db, campaign.id),
        selected_summary=duplication.summarise_source(db, campaign.id, variant_ids or None),
        targets=[
            DuplicationTarget(
                id=b.id, name=b.name, crossing=b.id != brand_id,
                modes=duplication.allowed_modes(
                    db, principal, source_brand_id=brand_id, target_brand_id=b.id,
                    enforced=enforced),
            )
            for b in targets
        ],
    )


@router.post(
    "/{campaign_id}/duplicate",
    response_model=CampaignDuplicated,
    status_code=201,
    summary="Duplicate a campaign, possibly into another brand",
    description=(
        "The JSON twin of the duplicate wizard. The source must be in the working "
        "brand (404 otherwise). **The target brand is checked against the caller's "
        "own grants, not the working brand's:** `campaigns.manage` there, and for "
        "`content_mode: copy` also `content.manage` there. A brand that does not "
        "exist and a brand the caller holds no grant on both answer 403, so the "
        "response never says which brands exist. A mode the boundary does not "
        "allow, or an empty `variant_ids`, is 409. Statuses are forced to draft; "
        "nothing that *happened* (snapshots, sends, history) comes across."
    ),
)
def duplicate_campaign_record(
    campaign_id: int,
    payload: CampaignDuplicate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    campaign = (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id, CampaignDB.brand_id == brand_id)
        .first()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    try:
        target = duplication.require_campaign_target(
            db,
            request_principal(request),
            target_brand_id=payload.target_brand_id,
            content_mode=payload.content_mode,
            enforced=auth_is_enforced(request),
        )
    except duplication.DuplicationForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))

    try:
        report = duplication.duplicate_campaign(
            db,
            campaign_id=campaign.id,
            target_brand_id=target.id,
            name=payload.name,
            content_mode=payload.content_mode,
            variant_ids=payload.variant_ids,
            principal=request_principal(request),
            enforced=auth_is_enforced(request),
        )
    except duplication.DuplicationForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))
    except duplication.DuplicationRefused as error:
        raise HTTPException(status_code=409, detail=str(error))

    audit.record_from_request(
        request, db, audit.CAMPAIGN_DUPLICATED,
        subject_type="campaign", subject_id=report.campaign_id,
        # The brand the copy now lives in; the source is in the detail.
        brand_id=report.target_brand_id, detail=report.as_detail(),
    )
    return CampaignDuplicated(
        campaign_id=report.campaign_id,
        source_campaign_id=report.source_campaign_id,
        source_brand_id=report.source_brand_id,
        target_brand_id=report.target_brand_id,
        content_mode=report.content_mode,
        crossed_brands=report.crossed_brands,
        variants=report.variants,
        modules=report.modules,
        decision_slots=report.decision_slots,
        content_records_copied=report.content_records_copied,
        url_carriers=report.url_carriers,
        overrides_carried=report.overrides_carried,
        overrides_not_carried=report.overrides_not_carried,
    )


@router.post(
    "/variants/{variant_id}/duplicate",
    response_model=VariantDuplicated,
    status_code=201,
    summary="Duplicate a variant, by default beside the original",
    description=(
        "The primary way a variant is created (task-229). Same brand only: the "
        "variant and `target_campaign_id` (default: its own campaign) must be in "
        "the working brand, 404 otherwise. `content_mode` defaults to `keep` "
        "inside the own campaign and `layout` into another; `copy` is 409. "
        "Status is draft, slots arrive unconfigured, nothing that happened comes "
        "across."
    ),
)
def duplicate_variant_record(
    variant_id: int,
    payload: VariantDuplicate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        report = duplication.duplicate_variant(
            db,
            variant_id=variant_id,
            brand_id=brand_id,
            target_campaign_id=payload.target_campaign_id,
            name=payload.name,
            content_mode=payload.content_mode,
            principal=request_principal(request),
            enforced=auth_is_enforced(request),
        )
    except duplication.DuplicationNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    except duplication.DuplicationForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))
    except duplication.DuplicationRefused as error:
        raise HTTPException(status_code=409, detail=str(error))

    audit.record_from_request(
        request, db, audit.VARIANT_DUPLICATED,
        subject_type="variant", subject_id=report.variant_id,
        brand_id=brand_id, detail=report.as_detail(),
    )
    return VariantDuplicated(
        variant_id=report.variant_id,
        source_variant_id=report.source_variant_id,
        campaign_id=report.campaign_id,
        source_campaign_id=report.source_campaign_id,
        content_mode=report.content_mode,
        modules=report.modules,
        decision_slots=report.decision_slots,
        url_carriers=report.url_carriers,
        overrides_carried=report.overrides_carried,
        overrides_not_carried=report.overrides_not_carried,
    )


@router.get(
    "/variants/{variant_id}/suggestions",
    response_model=list[SuggestionRun],
    summary="Every AI subject/preheader suggestion for this variant, newest first",
    description=(
        "Reads back what `POST /campaigns/variants/{id}/suggest-subject` started: "
        "the options, the notices to show before using one, the raw reply when "
        "nothing parsed, the prompt version and the tokens. 404 when the variant "
        "is not in the working brand."
    ),
)
def get_variant_suggestions(
    variant_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.ai.service import suggestions_for_variant

    runs = suggestions_for_variant(db, variant_id, brand_id=brand_id)
    if runs is None:
        raise HTTPException(status_code=404, detail=f"Variant {variant_id} not found")
    return runs


@router.get(
    "/decision-slots",
    response_model=Page[DecisionSlotListed],
    summary="Every decision slot in the working brand, with its resolution counts",
)
def get_decision_slots(
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.campaigns.service import page_decision_slots_with_stats

    return page_decision_slots_with_stats(db, params, brand_id=brand_id)


@router.get(
    "/decision-slots/{slot_id}/stats",
    response_model=DecisionSlotStats,
    summary="What one decision slot has picked: summary, top content, latest, reasons",
)
def get_decision_slot_stats(
    slot_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.campaigns.service import decision_slot_stats

    stats = decision_slot_stats(db, slot_id, brand_id=brand_id)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Decision slot {slot_id} not found")
    return {**stats, "slot": to_decision_slot(stats["slot"])}


@router.get(
    "/decision-slots/{slot_id}/candidates",
    response_model=SlotCandidates,
    summary="How many content records one decision slot would choose between",
    description=(
        "Counted over the same query the strategy picks from, without picking: "
        "nothing is resolved or written. For a strategy that picks per recipient, "
        "one person may be offered fewer."
    ),
)
def get_decision_slot_candidates(
    slot_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.campaigns.service import slot_candidate_count
    from app.decision.strategies.base import BrokenCampaignChain

    try:
        candidates = slot_candidate_count(db, slot_id, brand_id=brand_id)
    except BrokenCampaignChain as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if candidates is None:
        raise HTTPException(status_code=404, detail=f"Decision slot {slot_id} not found")
    return candidates


@router.get(
    "/{campaign_id}/composition",
    response_model=CampaignComposition,
    summary="A campaign as the variant editor shows it",
    description=(
        "Each variant's modules in order, with whether each may be overridden and "
        "its active override; the envelope module apart; the channel's module "
        "limit and whether another module fits; the module types it accepts; and "
        "each decision slot with its counts. 404 outside the working brand."
    ),
)
def get_campaign_composition(
    campaign_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.campaigns.service import campaign_composition

    composition = campaign_composition(db, campaign_id, brand_id=brand_id)
    if composition is None:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return composition
