from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB, AudienceRuleBlockDB
from app.recipients.db_models import RecipientDB
from app.recipients.service import CONSENTING_STATUS
from app.insight.signals import operational_signals_for_category

# Default minimum signal a system-suggested include block asks for. Deliberately
# low: the first suggestion should be inclusive ("anyone who's shown interest in
# this topic") and let the manager tighten it live — same broad-then-narrow
# stance as the override layer. On the operational-signal scale (declared
# interest ≈ 90, each click ≈ 5, decaying) this keeps recipients with any
# lingering positive signal for the category.
DEFAULT_SUGGESTION_MIN_SCORE = 1.0


def list_groups(db: Session) -> list[AudienceGroupDB]:
    return db.query(AudienceGroupDB).order_by(AudienceGroupDB.name.asc()).all()


def get_group(db: Session, group_id: int) -> AudienceGroupDB | None:
    return db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group_id).first()


def create_group(
    db: Session, name: str, description: str | None = None, source_campaign_id: int | None = None
) -> AudienceGroupDB:
    group = AudienceGroupDB(name=name, description=description, source_campaign_id=source_campaign_id)
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An audience group named '{name}' already exists")
    db.refresh(group)
    return group


def update_group(
    db: Session, group_id: int, name: str, description: str | None = None
) -> AudienceGroupDB | None:
    group = get_group(db, group_id)
    if not group:
        return None
    group.name = name
    group.description = description
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An audience group named '{name}' already exists")
    db.refresh(group)
    return group


def delete_group(db: Session, group_id: int) -> bool:
    group = get_group(db, group_id)
    if not group:
        return False
    # Clear both children first — members and rule blocks both FK to the group,
    # so either left behind blocks the delete.
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group_id).delete()
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id == group_id).delete()
    db.delete(group)
    db.commit()
    return True


def list_members(db: Session, group_id: int) -> list[AudienceGroupMemberDB]:
    return (
        db.query(AudienceGroupMemberDB)
        .filter(AudienceGroupMemberDB.group_id == group_id)
        .all()
    )


def add_member(db: Session, group_id: int, recipient_id: int) -> AudienceGroupMemberDB | None:
    existing = (
        db.query(AudienceGroupMemberDB)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupMemberDB.recipient_id == recipient_id,
        )
        .first()
    )
    if existing:
        return existing
    member = AudienceGroupMemberDB(group_id=group_id, recipient_id=recipient_id)
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent call won the TOCTOU race between the check above and
        # this insert — the unique constraint caught it; treat it the same
        # as "already a member" rather than surfacing a raw 500.
        db.rollback()
        return (
            db.query(AudienceGroupMemberDB)
            .filter(
                AudienceGroupMemberDB.group_id == group_id,
                AudienceGroupMemberDB.recipient_id == recipient_id,
            )
            .first()
        )
    db.refresh(member)
    return member


def remove_member(db: Session, group_id: int, recipient_id: int) -> bool:
    member = (
        db.query(AudienceGroupMemberDB)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupMemberDB.recipient_id == recipient_id,
        )
        .first()
    )
    if not member:
        return False
    db.delete(member)
    db.commit()
    return True


def get_member_recipient_ids(db: Session, group_id: int) -> set[int]:
    rows = (
        db.query(AudienceGroupMemberDB.recipient_id)
        .filter(AudienceGroupMemberDB.group_id == group_id)
        .all()
    )
    return {r.recipient_id for r in rows}


def find_by_criteria(
    db: Session,
    *,
    language: str | None = None,
    status: str | None = None,
    preference_category_id: int | None = None,
    min_preference_score: float | None = None,
    exclude_ids: set[int] | None = None,
) -> list[RecipientDB]:
    # Consent gate: audiences are resolved only from consenting recipients.
    # Filtering here — at audience-resolution time, before any decisioning or
    # rendering runs — is deliberate (F1 in docs/backlog.md): it keeps
    # non-consenting recipients out of the processing scope entirely, both for
    # GDPR reasons (running the decision engine over their data is itself
    # "processing") and cost reasons (no paid AI/token spend on people who will
    # never receive anything). "pending" and "opted_out" are both excluded.
    q = db.query(RecipientDB).filter(RecipientDB.consent_status == CONSENTING_STATUS)

    if language:
        q = q.filter(RecipientDB.language == language)
    if status:
        q = q.filter(RecipientDB.status == status)
    if exclude_ids:
        q = q.filter(RecipientDB.id.notin_(exclude_ids))

    records = q.order_by(RecipientDB.email.asc()).all()

    # Preference criterion: keep recipients whose *operational signal* for the
    # category clears the threshold (ADR-132, decay-on-read). Computed rather
    # than SQL-joined against a stored score, since there is no stored score.
    if preference_category_id is not None:
        min_score = min_preference_score if min_preference_score is not None else 0.0
        signals = operational_signals_for_category(db, preference_category_id)
        records = [r for r in records if signals.get(r.id, 0.0) >= min_score]

    # RecipientDB.email has no unique constraint (a hard-unique decision is
    # deferred) — dedupe by email here so a bad import with duplicate-email
    # rows doesn't inflate or double-count a segment preview.
    seen_emails: set[str] = set()
    deduplicated: list[RecipientDB] = []
    for record in records:
        if record.email in seen_emails:
            continue
        seen_emails.add(record.email)
        deduplicated.append(record)

    return deduplicated


def bulk_add_members(db: Session, group_id: int, recipient_ids: list[int]) -> int:
    existing = get_member_recipient_ids(db, group_id)
    added = 0
    for rid in recipient_ids:
        if rid not in existing:
            db.add(AudienceGroupMemberDB(group_id=group_id, recipient_id=rid))
            added += 1
    if not added:
        return added

    try:
        db.commit()
    except IntegrityError:
        # A concurrent call added one of these rows between the check above
        # and this commit. Fall back to committing one at a time so a
        # single conflicting row doesn't lose the rest of a legitimate
        # batch — each conflicting insert is skipped, not fatal.
        db.rollback()
        added = 0
        for rid in recipient_ids:
            if rid in existing:
                continue
            db.add(AudienceGroupMemberDB(group_id=group_id, recipient_id=rid))
            try:
                db.commit()
                added += 1
            except IntegrityError:
                db.rollback()

    return added


# ---------------------------------------------------------------------------
# Rule blocks — live, editable criteria that make up a group's audience
# ---------------------------------------------------------------------------

def _recipients_for_criteria(db: Session, criteria: dict) -> list[RecipientDB]:
    """Resolve one block's criteria to consenting recipients. Thin adapter over
    find_by_criteria so blocks and the older bulk-add path share one definition
    of what a criterion means."""
    criteria = criteria or {}
    cat = criteria.get("category_id")
    return find_by_criteria(
        db,
        language=criteria.get("language") or None,
        status=criteria.get("status") or None,
        preference_category_id=int(cat) if cat not in (None, "") else None,
        min_preference_score=criteria.get("min_score"),
    )


def count_for_criteria(db: Session, criteria: dict) -> int:
    return len(_recipients_for_criteria(db, criteria))


def list_blocks(db: Session, group_id: int) -> list[AudienceRuleBlockDB]:
    return (
        db.query(AudienceRuleBlockDB)
        .filter(AudienceRuleBlockDB.group_id == group_id)
        .order_by(AudienceRuleBlockDB.kind.asc(), AudienceRuleBlockDB.position.asc(), AudienceRuleBlockDB.id.asc())
        .all()
    )


def get_block(db: Session, block_id: int) -> AudienceRuleBlockDB | None:
    return db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.id == block_id).first()


def add_block(
    db: Session,
    group_id: int,
    kind: str = "include",
    criteria: dict | None = None,
    label: str | None = None,
    source: str = "manual",
) -> AudienceRuleBlockDB:
    if kind not in ("include", "exclude"):
        raise ValueError("kind must be 'include' or 'exclude'")
    next_pos = (
        db.query(AudienceRuleBlockDB)
        .filter(AudienceRuleBlockDB.group_id == group_id)
        .count()
    )
    block = AudienceRuleBlockDB(
        group_id=group_id,
        kind=kind,
        criteria=criteria or {},
        label=label,
        source=source,
        position=next_pos,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def update_block(
    db: Session,
    block_id: int,
    kind: str | None = None,
    criteria: dict | None = None,
    label: str | None = None,
) -> AudienceRuleBlockDB | None:
    block = get_block(db, block_id)
    if not block:
        return None
    if kind is not None:
        if kind not in ("include", "exclude"):
            raise ValueError("kind must be 'include' or 'exclude'")
        block.kind = kind
    if criteria is not None:
        block.criteria = criteria
    if label is not None:
        block.label = label
    db.commit()
    db.refresh(block)
    return block


def delete_block(db: Session, block_id: int) -> bool:
    block = get_block(db, block_id)
    if not block:
        return False
    db.delete(block)
    db.commit()
    return True


def resolve_audience(db: Session, group_id: int) -> list[RecipientDB]:
    """The group's live audience:
        (∪ include blocks) ∪ (manual member pins) − (∪ exclude blocks)
    then re-gated to consenting recipients so a pin added before someone
    opted out can never leak back in (the consent floor always applies)."""
    blocks = list_blocks(db, group_id)

    include_ids: set[int] = set()
    exclude_ids: set[int] = set()
    for block in blocks:
        ids = {r.id for r in _recipients_for_criteria(db, block.criteria)}
        if block.kind == "exclude":
            exclude_ids |= ids
        else:
            include_ids |= ids

    # Manual pins (existing static membership) count as include pins — "keep
    # both": hand-picked recipients survive alongside the live rules.
    include_ids |= get_member_recipient_ids(db, group_id)

    final_ids = include_ids - exclude_ids
    if not final_ids:
        return []

    records = (
        db.query(RecipientDB)
        .filter(
            RecipientDB.id.in_(final_ids),
            RecipientDB.consent_status == CONSENTING_STATUS,  # consent floor
        )
        .order_by(RecipientDB.email.asc())
        .all()
    )
    return records


# ---------------------------------------------------------------------------
# System-suggested audience — content/category driven (use case 1)
# ---------------------------------------------------------------------------

def campaign_category_scores(db: Session, campaign_id: int) -> list[dict]:
    """Rank the categories a campaign's content is about, so a suggestion can
    target recipients interested in those topics. Content reaches a category two
    ways: a module bound directly to a content record, and a decision slot whose
    picks were resolved to content records (ADR-083 personalization). Both are
    summed by category via the content↔category assignment scores."""
    from app.campaigns.db_models import VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
    from app.content.db_models import ContentCategoryAssignmentDB, CategoryDB

    variant_ids = [v.id for v in db.query(VariantDB.id).filter(VariantDB.campaign_id == campaign_id).all()]
    if not variant_ids:
        return []

    content_ids: set[int] = set()
    # Direct module → content record.
    for (crid,) in (
        db.query(ModuleInstanceDB.content_record_id)
        .filter(ModuleInstanceDB.variant_id.in_(variant_ids), ModuleInstanceDB.content_record_id.isnot(None))
        .all()
    ):
        content_ids.add(crid)
    # Decision slot → resolved picks.
    slot_ids = [s.id for s in db.query(DecisionSlotDB.id).filter(DecisionSlotDB.variant_id.in_(variant_ids)).all()]
    if slot_ids:
        for (crid,) in (
            db.query(DecisionResolutionDB.content_record_id)
            .filter(DecisionResolutionDB.decision_slot_id.in_(slot_ids))
            .distinct()
            .all()
        ):
            content_ids.add(crid)

    if not content_ids:
        return []

    scores: dict[int, int] = {}
    for assignment in (
        db.query(ContentCategoryAssignmentDB)
        .filter(ContentCategoryAssignmentDB.content_id.in_(content_ids))
        .all()
    ):
        scores[assignment.category_id] = scores.get(assignment.category_id, 0) + (assignment.score or 0)

    if not scores:
        return []

    names = {c.id: c.name for c in db.query(CategoryDB).filter(CategoryDB.id.in_(scores.keys())).all()}
    ranked = [
        {"category_id": cid, "category_name": names.get(cid, f"Category {cid}"), "content_score": total}
        for cid, total in scores.items()
    ]
    ranked.sort(key=lambda r: r["content_score"], reverse=True)
    return ranked


def suggest_include_blocks_for_campaign(db: Session, campaign_id: int, max_categories: int = 5) -> list[dict]:
    """Proposed (not yet persisted) include blocks for a campaign: one per top
    category its content covers, each with a default min-score and a live count
    so the manager sees the impact before accepting."""
    suggestions = []
    for row in campaign_category_scores(db, campaign_id)[:max_categories]:
        criteria = {"category_id": row["category_id"], "min_score": DEFAULT_SUGGESTION_MIN_SCORE}
        suggestions.append({
            "label": f"Interested in {row['category_name']}",
            "criteria": criteria,
            "content_score": row["content_score"],
            "count": count_for_criteria(db, criteria),
        })
    return suggestions


def create_suggested_group_for_campaign(db: Session, campaign_id: int, campaign_name: str) -> AudienceGroupDB:
    """Materialize a new group seeded with the campaign's suggested include
    blocks. Blocks are marked source='suggested' so the UI can badge them as the
    system's proposal — fully editable/deletable, never a locked list."""
    base_name = f"{campaign_name} — suggested audience"
    name = base_name
    suffix = 2
    while db.query(AudienceGroupDB).filter(func.lower(AudienceGroupDB.name) == name.lower()).first():
        name = f"{base_name} ({suffix})"
        suffix += 1

    group = create_group(
        db,
        name,
        description=f"System-suggested from campaign #{campaign_id} content categories.",
        source_campaign_id=campaign_id,
    )
    for suggestion in suggest_include_blocks_for_campaign(db, campaign_id):
        add_block(
            db,
            group_id=group.id,
            kind="include",
            criteria=suggestion["criteria"],
            label=suggestion["label"],
            source="suggested",
        )
    return group


def recalculate_suggested_blocks(db: Session, group_id: int) -> AudienceGroupDB | None:
    """Re-derive a group's suggested include blocks from its source campaign's
    *current* content — for after a manager adjusts slots/content. Applies only
    the delta so nothing else is disturbed:
      • categories the campaign no longer covers → their suggested block removed
      • categories newly covered → a fresh suggested block added
      • a surviving category's suggested block is left untouched, preserving any
        threshold the manager already tuned on it
    Manual blocks and manual member pins are never touched. Returns None if the
    group has no source campaign to recalculate against."""
    group = get_group(db, group_id)
    if not group or not group.source_campaign_id:
        return None

    desired = suggest_include_blocks_for_campaign(db, group.source_campaign_id)
    desired_by_cat = {s["criteria"]["category_id"]: s for s in desired}

    existing_suggested = [b for b in list_blocks(db, group_id) if b.source == "suggested"]
    existing_cats = {(b.criteria or {}).get("category_id") for b in existing_suggested}

    # Remove suggested blocks whose category dropped out of the campaign.
    removed = 0
    for block in existing_suggested:
        if (block.criteria or {}).get("category_id") not in desired_by_cat:
            db.delete(block)
            removed += 1
    if removed:
        db.commit()

    # Add suggested blocks for newly-covered categories.
    added = 0
    for cat_id, suggestion in desired_by_cat.items():
        if cat_id not in existing_cats:
            add_block(
                db,
                group_id=group_id,
                kind="include",
                criteria=suggestion["criteria"],
                label=suggestion["label"],
                source="suggested",
            )
            added += 1

    return group
