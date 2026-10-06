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
    AudienceGroupUpdate,
    CriteriaValues,
    MemberAdd,
    PasteApplyRequest,
    PastePreview,
    PastePreviewRequest,
    PasteResult,
)
from app.audit import service as audit
from app.auth.dependencies import request_principal, working_brand
from app.campaigns.router import IF_MATCH, _expected
from app.campaigns.service import StaleWrite
from app.channels.registry import is_registered
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db


router = APIRouter(prefix="/api/audience-groups", tags=["audience"])


# --- writes: one version, audit, validated rules (task-295) -----------------
#
# Every write states the group's version in If-Match (ADR-180 point 2) and is
# audited (ADR-153 point 4); the group is one thing with one version, so a
# rule or member write moves it too (the Audience Write Surface final design
# pass, decision 10). No token, no check — the Jinja forms send none.

def record_write(request: Request, db: Session, action: str, group_id: int, detail: dict | None = None) -> None:
    """One audit entry for an audience write, on either plane (the Jinja forms use it too)."""
    audit.record_from_request(request, db, action, subject_type="audience_group", subject_id=group_id,
                              detail=detail or {})


def _stale(error: StaleWrite) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


def _criteria_refused(error: service.CriteriaInvalid) -> HTTPException:
    """A 422 in FastAPI's own shape, one entry per field, as the composer's."""
    return HTTPException(status_code=422, detail=[
        {"loc": ["body", "criteria", field], "msg": message, "type": "value_error"}
        for field, message in error.errors
    ])


def who(request: Request) -> str | None:
    """The readable label of whoever is writing, on either plane: the JSON
    guard's principal, else the Jinja session's person."""
    from app.auth.db_models import IntegrationDB, UserDB
    from app.auth.service import actor_label

    principal = request_principal(request)
    if isinstance(principal, (UserDB, IntegrationDB)):
        return actor_label(principal)
    # The Jinja plane resolves no principal; its session person is a summary.
    current = getattr(request.state, "current_user", None)
    if isinstance(current, dict) and current.get("email"):
        return current["email"]
    return actor_label(None)


@router.get("/criteria-values", response_model=CriteriaValues,
            summary="The languages and statuses a rule can choose from")
def get_criteria_values(db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    """Values among the people this brand has a consent record with — values, never people."""
    return service.criteria_values(db, brand_id=brand_id)


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
    q: str | None = Query(None, description="Find by name (part, any case)."),
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
        for row in service.list_groups_with_counts(db, brand_id=brand_id, channel=channel, q=q)
    ], params)


@router.post("/", response_model=AudienceGroup, status_code=201)
def create_group(
    payload: AudienceGroupCreate,
    request: Request,
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
        group = service.create_group(
            db, payload.name, brand_id=brand_id,
            description=payload.description,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    record_write(request, db, audit.AUDIENCE_GROUP_CREATED, group.id,
           {"name": group.name, "description": group.description})
    return group


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
        arithmetic=preview["arithmetic"],
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
def update_group(
    group_id: int, payload: AudienceGroupUpdate, request: Request,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH,
):
    """Rename or re-describe. Only the fields sent change; `description: null` clears it."""
    sent = payload.model_fields_set
    if "name" in sent and not (payload.name or "").strip():
        raise HTTPException(status_code=422, detail="A group needs a name")
    changes = {k: getattr(payload, k) for k in ("name", "description") if k in sent}
    try:
        group = service.update_group(db, group_id, brand_id=brand_id, expected_updated_at=_expected(if_match),
                                     **changes)
    except StaleWrite as error:
        raise _stale(error)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    record_write(request, db, audit.AUDIENCE_GROUP_UPDATED, group_id, changes)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int, request: Request, db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH,
):
    """Delete a group no send uses; one a send uses is refused 409, naming the sends."""
    group = service.get_group(db, group_id, brand_id=brand_id)
    name = group.name if group else None
    try:
        deleted = service.delete_group(db, group_id, brand_id=brand_id, expected_updated_at=_expected(if_match))
    except StaleWrite as error:
        raise _stale(error)
    except service.GroupInUse as error:
        raise HTTPException(status_code=409, detail=str(error))
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    record_write(request, db, audit.AUDIENCE_GROUP_DELETED, group_id, {"name": name})


@router.get("/{group_id}/members", response_model=Page[AudienceGroupMember])
def list_members(
    group_id: int, params: PageParams = Depends(page_params),
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    return service.page_members(db, group_id, params, brand_id=brand_id)


@router.post("/{group_id}/members/paste-preview", response_model=PastePreview,
             summary="What pasting a list of people would do, before anything is added")
def paste_preview(group_id: int, payload: PastePreviewRequest, db: Session = Depends(get_db),
                  brand_id: int = Depends(working_brand)):
    """Identifiers or email addresses, any separator, up to 5,000 (task-295)."""
    if not is_registered(payload.channel):
        raise HTTPException(status_code=422, detail=f"{payload.channel!r} is not a registered channel.")
    group = service.get_group(db, group_id, brand_id=brand_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Audience group not found")
    try:
        return service.paste_preview(db, group, payload.text, channel=payload.channel)
    except service.PasteTooLong as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.post("/{group_id}/members/paste", response_model=PasteResult,
             summary="Add a pasted list of people by hand, with one reason")
def paste_apply(group_id: int, payload: PasteApplyRequest, request: Request, db: Session = Depends(get_db),
                brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH):
    """Nobody is created: an entry that is not a recipient stays not found (ADR-120)."""
    group = service.get_group(db, group_id, brand_id=brand_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Audience group not found")
    try:
        result = service.paste_apply(db, group, payload.text, reason=payload.reason, added_by=who(request),
                                     expected_updated_at=_expected(if_match))
    except StaleWrite as error:
        raise _stale(error)
    except service.PasteTooLong as error:
        raise HTTPException(status_code=422, detail=str(error))
    record_write(request, db, audit.AUDIENCE_PEOPLE_PASTED, group_id, {**result, "reason": payload.reason})
    return result


@router.post("/{group_id}/members/{recipient_id}", response_model=AudienceGroupMember, status_code=201)
def add_member(
    group_id: int, recipient_id: int, request: Request, payload: MemberAdd | None = None,
    db: Session = Depends(get_db), brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH,
):
    """Add one person by hand, with an optional reason; who added them is recorded."""
    reason = payload.reason if payload else None
    try:
        result = service.pin(db, group_id, recipient_id, brand_id=brand_id, reason=reason,
                             added_by=who(request), expected_updated_at=_expected(if_match))
    except StaleWrite as error:
        raise _stale(error)
    if not result:
        raise HTTPException(status_code=404, detail="Group or recipient not found")
    member, created = result
    if created:
        record_write(request, db, audit.AUDIENCE_MEMBER_ADDED, group_id,
               {"recipient_id": recipient_id, "reason": member.reason})
    return member


@router.delete("/{group_id}/members/{recipient_id}", status_code=204)
def remove_member(
    group_id: int, recipient_id: int, request: Request, db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH,
):
    try:
        removed = service.remove_member(db, group_id, recipient_id, brand_id=brand_id,
                                        expected_updated_at=_expected(if_match))
    except StaleWrite as error:
        raise _stale(error)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")
    record_write(request, db, audit.AUDIENCE_MEMBER_REMOVED, group_id, {"recipient_id": recipient_id})


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
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
    if_match: str | None = IF_MATCH,
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
        block = service.add_block(
            db, group_id=group_id, kind=payload.kind,
            criteria=payload.criteria, label=payload.label,
            brand_id=brand_id, expected_updated_at=_expected(if_match),
        )
    except StaleWrite as error:
        raise _stale(error)
    except service.CriteriaInvalid as error:
        raise _criteria_refused(error)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    record_write(request, db, audit.AUDIENCE_RULE_ADDED, group_id,
           {"block_id": block.id, "kind": block.kind, "criteria": block.criteria, "label": block.label})
    return block


@router.patch("/{group_id}/blocks/{block_id}", response_model=AudienceRuleBlock)
def edit_block(
    group_id: int,
    block_id: int,
    payload: AudienceRuleBlockUpdate,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
    if_match: str | None = IF_MATCH,
):
    """Change a rule. Only the fields sent change; `label: null` clears the label."""
    block = service.get_block(db, block_id, brand_id=brand_id)
    if block is None or block.group_id != group_id:
        raise HTTPException(status_code=404, detail="Rule block not found")
    label = payload.label if "label" in payload.model_fields_set else service.UNSET
    try:
        updated = service.update_block(
            db, block_id=block_id, kind=payload.kind,
            criteria=payload.criteria, label=label,
            brand_id=brand_id, expected_updated_at=_expected(if_match),
        )
    except StaleWrite as error:
        raise _stale(error)
    except service.CriteriaInvalid as error:
        raise _criteria_refused(error)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    record_write(request, db, audit.AUDIENCE_RULE_CHANGED, group_id,
           {"block_id": block_id, "kind": updated.kind, "criteria": updated.criteria, "label": updated.label})
    return updated


@router.delete("/{group_id}/blocks/{block_id}", status_code=204)
def remove_block(
    group_id: int, block_id: int, request: Request, db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH,
):
    block = service.get_block(db, block_id, brand_id=brand_id)
    if block is None or block.group_id != group_id:
        raise HTTPException(status_code=404, detail="Rule block not found")
    detail = {"block_id": block_id, "kind": block.kind, "criteria": block.criteria, "label": block.label}
    try:
        service.delete_block(db, block_id, brand_id=brand_id, expected_updated_at=_expected(if_match))
    except StaleWrite as error:
        raise _stale(error)
    record_write(request, db, audit.AUDIENCE_RULE_REMOVED, group_id, detail)


@router.post("/{group_id}/members", status_code=200)
def bulk_add(
    group_id: int,
    payload: BulkAddRequest,
    request: Request,
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
    if added:
        record_write(request, db, audit.AUDIENCE_PEOPLE_PASTED, group_id,
               {"added": added, "requested": len(payload.recipient_ids), "by": "recipient ids"})
    return {"added": added, "requested": len(payload.recipient_ids)}


@router.post("/{group_id}/recalculate", response_model=AudienceGroup)
def recalculate(group_id: int, request: Request, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
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
    record_write(request, db, audit.AUDIENCE_RULES_RECALCULATED, group_id,
           {"source_campaign_id": updated.source_campaign_id})
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
    group_id: int, payload: BulkAddByCriteria, request: Request,
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
    record_write(request, db, audit.AUDIENCE_PEOPLE_PASTED, group_id,
           {"by": "criteria", "criteria": payload.model_dump(exclude={"channel"}), "channel": payload.channel,
            "result": result if isinstance(result, dict) else None})
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
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.campaigns.service import get_campaign

    campaign = get_campaign(db, payload.campaign_id, brand_id=brand_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign {payload.campaign_id} not found")
    try:
        group = service.create_suggested_group_for_campaign(
            db, campaign.id, campaign.name, brand_id=brand_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    record_write(request, db, audit.AUDIENCE_GROUP_CREATED, group.id,
           {"name": group.name, "source_campaign_id": campaign.id})
    return group
