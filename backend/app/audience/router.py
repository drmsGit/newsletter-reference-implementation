from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audience import service
from app.audience.models import (
    AudienceGroup,
    AudienceGroupCreate,
    AudienceGroupMember,
    AudienceRuleBlock,
    AudienceRuleBlockCreate,
    AudienceRuleBlockUpdate,
    BulkAddRequest,
)
from app.auth.dependencies import working_brand
from app.database import get_db


router = APIRouter(prefix="/api/audience-groups", tags=["audience"])


@router.get("/", response_model=list[AudienceGroup])
def list_groups(db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    return service.list_groups(db, brand_id=brand_id)


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


@router.get("/{group_id}/members", response_model=list[AudienceGroupMember])
def list_members(group_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    return service.list_members(db, group_id, brand_id=brand_id)


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
