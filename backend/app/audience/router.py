from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audience import service
from app.audience.models import (
    AudienceGroup,
    AudienceGroupCreate,
    AudienceGroupListed,
    AudiencePreview,
    PreviewBlock,
    PreviewRecipient,
    BulkAddByCriteria,
    BulkAddResult,
    CriteriaPreview,
    SuggestedAudienceRequest,
    AudienceGroupMember,
    AudienceRuleBlock,
    AudienceRuleBlockCreate,
    AudienceRuleBlockUpdate,
    BulkAddRequest,
)
from app.auth.dependencies import working_brand
from app.channels.registry import is_registered
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db


router = APIRouter(prefix="/api/audience-groups", tags=["audience"])


@router.get(
    "/",
    response_model=Page[AudienceGroupListed],
    summary="The brand's audience groups, with counts",
    description=(
        "Each group with its pinned-member count. Pass `channel` to add the live, "
        "consent-gated recipient count for that channel — the number a send on "
        "that channel would reach. **Without `channel` there is no recipient "
        "count** (ADR-176 point 5: a group resolves to different people per "
        "channel, so a channel-less number would be a guess). Asking for counts "
        "resolves every group, so it costs one resolution per group."
    ),
)
def list_groups(
    channel: str | None = Query(default=None),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    if channel is not None and not is_registered(channel):
        raise HTTPException(status_code=422, detail=f"{channel!r} is not a registered channel.")
    # Counts are assembled per group (task-213 records the cost), so this
    # pages the assembled list (ADR-185, `page_of_list`).
    return page_of_list([
        AudienceGroupListed(
            id=row["group"].id, name=row["group"].name, description=row["group"].description,
            created_at=row["group"].created_at, updated_at=row["group"].updated_at,
            source_campaign_id=row["group"].source_campaign_id,
            pinned_count=row["pinned_count"], recipient_count=row["recipient_count"],
            count_channel=row["count_channel"],
        )
        for row in service.list_groups_with_counts(db, brand_id=brand_id, channel=channel)
    ], params)


@router.post("/", response_model=AudienceGroup, status_code=201)
def create_group(
    payload: AudienceGroupCreate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        # **Resolved 2026-09-19 (ADR-168).** `enforce_api_policy` writes the
        # brand it actually checked the permission against onto
        # `request.state.current_brand` — the declared `X-Brand` for a machine,
        # the session's working brand for a person — so this row lands in the
        # same brand the caller was authorised for. Writing to the default brand
        # while checking against a declared one was the gap.
        return service.create_group(
            db, payload.name, brand_id=brand_id,
            description=payload.description,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get("/{group_id}", response_model=AudienceGroup)
def get_group(group_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    group = service.get_group(db, group_id, brand_id=brand_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.get(
    "/{group_id}/preview",
    response_model=AudiencePreview,
    summary="What a send to this group on one channel would reach",
    description=(
        "Each rule block with its own count, the resolved audience, how many of "
        "them the send's own exclusion stack would actually reach (and why the "
        "rest drop, by stage), and the first 20 reachable recipients with their "
        "address on that channel. `channel` is required: a group resolves to "
        "different people per channel, so there is no channel-less preview "
        "(ADR-176 point 5)."
    ),
)
def preview_group(
    group_id: int,
    channel: str = Query(...),
    q: str | None = Query(None, description="Find recipients by identifier or address (part, any case)."),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    if not is_registered(channel):
        raise HTTPException(status_code=422, detail=f"{channel!r} is not a registered channel.")
    group = service.get_group(db, group_id, brand_id=brand_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Audience group not found")
    preview = service.preview_group(db, group, channel=channel, q=q)
    return AudiencePreview(
        group_id=group.id,
        channel=preview["channel"],
        blocks=[PreviewBlock(**b) for b in preview["blocks"]],
        resolved_count=preview["resolved_count"],
        reachable_count=preview["reachable_count"],
        unreachable_count=preview["unreachable_count"],
        dropped_by_stage=preview["dropped_by_stage"],
        sample_matching=preview["sample_matching"],
        sample=[
            PreviewRecipient(
                recipient_id=row["recipient"].id, external_id=row["recipient"].external_id,
                language=row["recipient"].language, status=row["recipient"].status,
                address=row["address"],
            )
            for row in preview["sample"]
        ],
    )


@router.patch("/{group_id}", response_model=AudienceGroup)
def update_group(group_id: int, payload: AudienceGroupCreate, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    try:
        group = service.update_group(db, group_id, payload.name, payload.description, brand_id=brand_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    if not service.delete_group(db, group_id, brand_id=brand_id):
        raise HTTPException(status_code=404, detail="Group not found")


@router.get("/{group_id}/members", response_model=Page[AudienceGroupMember])
def list_members(
    group_id: int, params: PageParams = Depends(page_params),
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    return service.page_members(db, group_id, params, brand_id=brand_id)


@router.post("/{group_id}/members/{recipient_id}", response_model=AudienceGroupMember, status_code=201)
def add_member(group_id: int, recipient_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    member = service.add_member(db, group_id, recipient_id, brand_id=brand_id)
    if not member:
        raise HTTPException(status_code=404, detail="Group or recipient not found")
    return member


@router.delete("/{group_id}/members/{recipient_id}", status_code=204)
def remove_member(group_id: int, recipient_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    if not service.remove_member(db, group_id, recipient_id, brand_id=brand_id):
        raise HTTPException(status_code=404, detail="Member not found")


# --- rule blocks, pins and suggestion (ADR-002) ----------------------------
#
# Added 2026-09-19. Groups and individual members existed over JSON; **rule
# blocks did not**, and a group's audience is evaluated live from its blocks
# rather than stored — so the API could create a group and could not say who it
# meant. That is most of what the audience screen does, and it is the second
# screen of the React MVP.

@router.get("/{group_id}/blocks", response_model=list[AudienceRuleBlock])
def get_blocks(group_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    return service.list_blocks(db, group_id, brand_id=brand_id)


@router.post("/{group_id}/blocks", response_model=AudienceRuleBlock, status_code=201)
def create_block(
    group_id: int,
    payload: AudienceRuleBlockCreate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Add an include or exclude rule.

    `source` is not accepted from the caller and is always `"manual"` here.
    The distinction between a hand-authored block and one a system suggested is
    provenance, and letting a request claim to be a suggestion would make the
    "visibly editable, visibly suggested" trust model (ADR-040/041's) a thing a
    caller can lie about.
    """
    if service.get_group(db, group_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Audience group not found")
    try:
        return service.add_block(
            db, group_id=group_id, kind=payload.kind,
            criteria=payload.criteria, label=payload.label,
            brand_id=brand_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.patch("/{group_id}/blocks/{block_id}", response_model=AudienceRuleBlock)
def edit_block(
    group_id: int,
    block_id: int,
    payload: AudienceRuleBlockUpdate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    block = service.get_block(db, block_id, brand_id=brand_id)
    if block is None or block.group_id != group_id:
        raise HTTPException(status_code=404, detail="Rule block not found")
    try:
        updated = service.update_block(
            db, block_id=block_id, kind=payload.kind,
            criteria=payload.criteria, label=payload.label,
            brand_id=brand_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return updated


@router.delete("/{group_id}/blocks/{block_id}", status_code=204)
def remove_block(group_id: int, block_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    block = service.get_block(db, block_id, brand_id=brand_id)
    if block is None or block.group_id != group_id:
        raise HTTPException(status_code=404, detail="Rule block not found")
    service.delete_block(db, block_id, brand_id=brand_id)


@router.post("/{group_id}/members", status_code=200)
def bulk_add(
    group_id: int,
    payload: BulkAddRequest,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Pin several recipients in one call.

    Returns how many were **added**, which is not the same as how many were
    asked for: a recipient already in the group is not an error and is not
    counted again. There is deliberately no bulk-remove counterpart yet — it is
    a logged gap rather than an oversight, and adding one here without the
    criteria-tracking that item asks for would make removal look symmetrical
    when it is not.
    """
    if service.get_group(db, group_id, brand_id=brand_id) is None:
        raise HTTPException(status_code=404, detail="Audience group not found")
    added = service.bulk_add_members(db, group_id, payload.recipient_ids, brand_id=brand_id)
    return {"added": added, "requested": len(payload.recipient_ids)}


@router.post("/{group_id}/recalculate", response_model=AudienceGroup)
def recalculate(group_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    """Re-derive this group's **suggested** blocks from its source campaign.

    Manual blocks are untouched — that is the whole point of `source` being on
    the block rather than on the group. A group with no source campaign has
    nothing to recalculate and says so rather than silently doing nothing.
    """
    updated = service.recalculate_suggested_blocks(db, group_id, brand_id=brand_id)
    if updated is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "That group has no source campaign, so there are no suggested "
                "blocks to re-derive."
            ),
        )
    return updated


@router.get(
    "/{group_id}/criteria-preview",
    response_model=CriteriaPreview,
    summary="Who ad-hoc criteria would add to this group, on one channel",
    description=(
        "Consenting on `channel` for the group's brand and not already members: "
        "a count and a 20-person sample with their address on that channel. "
        "`channel` is required (ADR-176 point 5)."
    ),
)
def criteria_preview(
    group_id: int,
    channel: str = Query(...),
    language: str | None = None,
    status: str | None = None,
    category_id: int | None = None,
    min_score: float | None = None,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.recipients.consent import resolve_send_addresses

    if not is_registered(channel):
        raise HTTPException(status_code=422, detail=f"{channel!r} is not a registered channel.")
    matches = service.criteria_matches(db, group_id, brand_id=brand_id, channel=channel, criteria={
        "language": language, "status": status, "category_id": category_id, "min_score": min_score,
    })
    if matches is None:
        raise HTTPException(status_code=404, detail="Audience group not found")
    sample = matches[:20]
    addresses = resolve_send_addresses(db, [r.id for r in sample], channel=channel)
    return CriteriaPreview(channel=channel, count=len(matches), sample=[
        PreviewRecipient(recipient_id=r.id, external_id=r.external_id, language=r.language,
                         status=r.status, address=addresses.get(r.id))
        for r in sample
    ])


@router.post(
    "/{group_id}/bulk-add",
    response_model=BulkAddResult,
    summary="Pin everyone the criteria match (needs audiences.manage)",
    description=(
        "Adds every consenting non-member the criteria match on `channel`. "
        "`audiences.manage`, not `audiences.pin`: a rule that adds hundreds "
        "reshapes the audience (decided 2026-10-02)."
    ),
)
def bulk_add_by_criteria(
    group_id: int, payload: BulkAddByCriteria,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    if not is_registered(payload.channel):
        raise HTTPException(status_code=422, detail=f"{payload.channel!r} is not a registered channel.")
    result = service.bulk_add_by_criteria(
        db, group_id, brand_id=brand_id, channel=payload.channel,
        criteria=payload.model_dump(exclude={"channel"}),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Audience group not found")
    return result


@router.post(
    "/suggested",
    response_model=AudienceGroup,
    status_code=201,
    summary="A suggested audience from a campaign's content categories",
    description=(
        "One editable include block per top category of the campaign's content. "
        "The campaign must be in the working brand (404 otherwise)."
    ),
)
def create_suggested_audience(
    payload: SuggestedAudienceRequest,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.campaigns.service import get_campaign

    campaign = get_campaign(db, payload.campaign_id, brand_id=brand_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign {payload.campaign_id} not found")
    try:
        return service.create_suggested_group_for_campaign(
            db, campaign.id, campaign.name, brand_id=brand_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
