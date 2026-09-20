import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB, AudienceRuleBlockDB
from app.recipients.db_models import RecipientDB
from app.recipients.consent import DEFAULT_CHANNEL, is_consenting_filter, resolve_emails
from app.insight.signals import operational_signals_for_category

logger = logging.getLogger(__name__)

# Default minimum signal a system-suggested include block asks for. Deliberately
# low: the first suggestion should be inclusive ("anyone who's shown interest in
# this topic") and let the manager tighten it live — same broad-then-narrow
# stance as the override layer. On the operational-signal scale (declared
# interest ≈ 90, each click ≈ 5, decaying) this keeps recipients with any
# lingering positive signal for the category.
DEFAULT_SUGGESTION_MIN_SCORE = 1.0


def list_groups(db: Session, *, brand_id: int) -> list[AudienceGroupDB]:
    """Audience groups, scoped to one brand (ADR-150 point 2).

    Brand here is **ownership, not membership**: the criteria behind a group
    resolve to the same people whichever brand asks, because a recipient
    carries no brand (point 9) and consent does not carry one yet. Making
    membership differ per brand is the Phase 2 consent work.

    **The brand is required since 2026-09-19** (ADR-172 point 4). It used to
    default to every brand, which meant a forgotten argument returned the whole
    platform rather than failing. `list_all_audience_groups` is the road for
    callers that genuinely span brands.
    """
    return (
        db.query(AudienceGroupDB)
        .filter(AudienceGroupDB.brand_id == brand_id)
        .order_by(AudienceGroupDB.name.asc())
        .all()
    )


def list_all_audience_groups(db: Session) -> list[AudienceGroupDB]:
    """Every group, across every brand — the ADR-172 point 4 escape hatch.

    For callers that legitimately have no working brand. Counted by
    `test_brand_boundary.py`; no router may reach for it.
    """
    return db.query(AudienceGroupDB).order_by(AudienceGroupDB.name.asc()).all()


def group_regardless_of_brand(db: Session, group_id: int) -> AudienceGroupDB | None:
    """A group without asking which brand the caller is in.

    **Deliberately unscoped, and there is exactly one legitimate use**:
    `resolve_audience`, which gates on the group's OWN brand and therefore has
    to find the group before it knows which brand that is. Scoping it there
    would be circular, and passing the caller's brand in would be wrong — a
    manager who switched brand between building a send and firing it must not
    change whose consent was checked.

    Every other caller wants `get_group`, which takes a brand and refuses
    outside it. This one is named at length so that reaching for it is a
    decision rather than an autocomplete.
    """
    return db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group_id).first()


def get_group(db: Session, group_id: int, *, brand_id: int) -> AudienceGroupDB | None:
    """One group, selected within a brand (ADR-172 points 4-6).

    The choke point for this module: update, delete, the member functions and
    the block functions all resolve through here, so scoping it once scopes
    them. A group in another brand is not found.
    """
    return (
        db.query(AudienceGroupDB)
        .filter(AudienceGroupDB.id == group_id, AudienceGroupDB.brand_id == brand_id)
        .first()
    )


def create_group(
    db: Session, name: str, brand_id: int, description: str | None = None,
    source_campaign_id: int | None = None,
) -> AudienceGroupDB:
    """A group belongs to a brand. **It deliberately does not belong to a
    channel**, and that was considered on 2026-09-18 rather than overlooked.

    The user asked whether groups should be created per channel. They should
    not, for the reason [[ADR-160 — Channel Model and Composition]] point 7
    gives about campaign coverage: a declared channel is *stored intent*, and
    stored intent "would create a drift class where intent and reality
    disagree with nobody clearing the stale state" — a group labelled push
    whose members are mostly email-only is exactly that.

    The alternative the user proposed is the one that is built: one group,
    targeted per sending channel. `resolve_audience` takes the channel, the
    consent floor is keyed to it (ADR-163 point 1), and the addressability
    stage filters on it — so the same group resolves to different people for an
    email send and a push send, and the send form shows both numbers. Nothing
    is stored, so nothing can go stale.
    """
    group = AudienceGroupDB(
        name=name, brand_id=brand_id, description=description,
        source_campaign_id=source_campaign_id,
    )
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An audience group named '{name}' already exists")
    db.refresh(group)
    return group


def update_group(
    db: Session, group_id: int, name: str, description: str | None = None,
    *, brand_id: int,
) -> AudienceGroupDB | None:
    group = get_group(db, group_id, brand_id=brand_id)
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


def delete_group(db: Session, group_id: int, *, brand_id: int) -> bool:
    group = get_group(db, group_id, brand_id=brand_id)
    if not group:
        return False
    # Clear both children first — members and rule blocks both FK to the group,
    # so either left behind blocks the delete.
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group_id).delete()
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id == group_id).delete()
    db.delete(group)
    db.commit()
    return True


def list_members(
    db: Session, group_id: int, *, brand_id: int
) -> list[AudienceGroupMemberDB]:
    """Pinned members, joined to the owning group (ADR-172 point 5).

    The membership row carries no brand and needs none — it hangs off the
    group, which has one.
    """
    return (
        db.query(AudienceGroupMemberDB)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceGroupMemberDB.group_id)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupDB.brand_id == brand_id,
        )
        .all()
    )


def add_member(
    db: Session, group_id: int, recipient_id: int, *, brand_id: int
) -> AudienceGroupMemberDB | None:
    # The group is resolved within the brand before a pin is written, so a
    # recipient cannot be pinned into another brand's list.
    if get_group(db, group_id, brand_id=brand_id) is None:
        return None

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


def remove_member(
    db: Session, group_id: int, recipient_id: int, *, brand_id: int
) -> bool:
    if get_group(db, group_id, brand_id=brand_id) is None:
        return False
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


def get_member_recipient_ids(db: Session, group_id: int, *, brand_id: int) -> set[int]:
    rows = (
        db.query(AudienceGroupMemberDB.recipient_id)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceGroupMemberDB.group_id)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupDB.brand_id == brand_id,
        )
        .all()
    )
    return {r.recipient_id for r in rows}


def find_by_criteria(
    db: Session,
    brand_id: int,
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
    # never receive anything).
    #
    # Reads the latest (recipient, email, marketing) consent event (ADR-163
    # point 1). Fail-closed in both directions: "pending" and "opted_out" are
    # excluded, and so is a recipient with no consent event at all, since the
    # absence of a decision is not a grant.
    # Consent is to a SENDER (ADR-163 addendum 2026-09-15), so the gate has
    # to ask "consenting to WHOM". Before brand_id was threaded here, every
    # brand's audience resolved against every brand's consent — the authoring
    # side was scoped and the send side was not.
    q = db.query(RecipientDB).filter(is_consenting_filter(brand_id))

    if language:
        q = q.filter(RecipientDB.language == language)
    if status:
        q = q.filter(RecipientDB.status == status)
    if exclude_ids:
        q = q.filter(RecipientDB.id.notin_(exclude_ids))

    # Ordered by id since the address is no longer a column (ADR-163 point 2).
    # This also makes deduplication deterministic: two recipients sharing an
    # address have no order between them under an email sort, so which one
    # survived was previously whatever the database happened to return. Now it
    # is the earliest-created, always.
    records = q.order_by(RecipientDB.id.asc()).all()

    # Preference criterion: keep recipients whose *operational signal* for the
    # category clears the threshold (ADR-132, decay-on-read). Computed rather
    # than SQL-joined against a stored score, since there is no stored score.
    if preference_category_id is not None:
        min_score = min_preference_score if min_preference_score is not None else 0.0
        signals = operational_signals_for_category(db, preference_category_id)
        records = [r for r in records if signals.get(r.id, 0.0) >= min_score]

    return _deduplicate_by_address(db, records)


def _deduplicate_by_address(
    db: Session, records: list[RecipientDB]
) -> list[RecipientDB]:
    """One address yields one recipient.

    Two recipient rows can legitimately share an address — a shared team inbox,
    `info@`, a household — so ADR-163's 2026-09-12 addendum (point 3) rejected a
    uniqueness constraint and put deduplication in the **addressability** stage
    of the point 7 exclusion stack instead. Without it the same inbox receives
    the send twice, and a segment preview over-reports.

    Deduplicating on the *resolved* address rather than `RecipientDB.email` is
    what makes this survive phase B, when that column goes away: a recipient is
    identified here by the address they would actually be sent to, chosen by the
    point 11 rules (primary flag, else most-recently-verified).

    A recipient with no usable address is dropped here too — they are not
    addressable on this channel, which is precisely what stage 1 means.

    Exclusions are logged rather than recorded to a table: the durable,
    per-recipient exclusion record point 8 requires arrives with the full
    ordered stack, in the P0 fix. Losing someone silently is the failure mode
    that made the P0 read as a rendering bug, so until then this at least says
    so out loud.
    """
    if not records:
        return []

    # One query for the whole candidate set, not one per recipient. ADR-163
    # point 10 requires each stage to be a set operation precisely so that
    # per-stage attribution does not cost the N+1 the send path is already
    # flagged for — resolving addresses in the loop would reintroduce it on the
    # audience path, where segments are largest.
    addresses = resolve_emails(db, [r.id for r in records])

    seen: set[str] = set()
    kept: list[RecipientDB] = []
    unaddressable: list[int] = []
    duplicates: list[int] = []
    for record in records:
        address = addresses.get(record.id)
        if not address:
            unaddressable.append(record.id)
            continue
        if address in seen:
            duplicates.append(record.id)
            continue
        seen.add(address)
        kept.append(record)

    # Logged in bulk for the same reason — one line per stage, not per person.
    if unaddressable:
        logger.info(
            "audience: %d recipient(s) excluded — no usable address on the "
            "email channel: %s",
            len(unaddressable),
            unaddressable,
        )
    if duplicates:
        logger.info(
            "audience: %d recipient(s) excluded — duplicate address, already "
            "covered by an earlier recipient in this resolution: %s",
            len(duplicates),
            duplicates,
        )
    return kept


def bulk_add_members(
    db: Session, group_id: int, recipient_ids: list[int], *, brand_id: int
) -> int:
    if get_group(db, group_id, brand_id=brand_id) is None:
        return 0
    existing = get_member_recipient_ids(db, group_id, brand_id=brand_id)
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

def _recipients_for_criteria(db: Session, criteria: dict, brand_id: int) -> list[RecipientDB]:
    """Resolve one block's criteria to consenting recipients. Thin adapter over
    find_by_criteria so blocks and the older bulk-add path share one definition
    of what a criterion means."""
    criteria = criteria or {}
    cat = criteria.get("category_id")
    return find_by_criteria(
        db,
        brand_id,
        language=criteria.get("language") or None,
        status=criteria.get("status") or None,
        preference_category_id=int(cat) if cat not in (None, "") else None,
        min_preference_score=criteria.get("min_score"),
    )


def count_for_criteria(db: Session, criteria: dict, brand_id: int) -> int:
    return len(_recipients_for_criteria(db, criteria, brand_id))


def list_blocks(
    db: Session, group_id: int, *, brand_id: int
) -> list[AudienceRuleBlockDB]:
    return (
        db.query(AudienceRuleBlockDB)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceRuleBlockDB.group_id)
        .filter(
            AudienceRuleBlockDB.group_id == group_id,
            AudienceGroupDB.brand_id == brand_id,
        )
        .order_by(AudienceRuleBlockDB.kind.asc(), AudienceRuleBlockDB.position.asc(), AudienceRuleBlockDB.id.asc())
        .all()
    )


def get_block(db: Session, block_id: int, *, brand_id: int) -> AudienceRuleBlockDB | None:
    """One rule block, via `block -> group -> brand` (ADR-172 point 5)."""
    return (
        db.query(AudienceRuleBlockDB)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceRuleBlockDB.group_id)
        .filter(AudienceRuleBlockDB.id == block_id, AudienceGroupDB.brand_id == brand_id)
        .first()
    )


def add_block(
    db: Session,
    group_id: int,
    kind: str = "include",
    criteria: dict | None = None,
    label: str | None = None,
    source: str = "manual",
    *,
    brand_id: int,
) -> AudienceRuleBlockDB:
    if kind not in ("include", "exclude"):
        raise ValueError("kind must be 'include' or 'exclude'")
    if get_group(db, group_id, brand_id=brand_id) is None:
        raise ValueError(f"Audience group {group_id} not found")
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
    *,
    brand_id: int,
) -> AudienceRuleBlockDB | None:
    block = get_block(db, block_id, brand_id=brand_id)
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


def delete_block(db: Session, block_id: int, *, brand_id: int) -> bool:
    block = get_block(db, block_id, brand_id=brand_id)
    if not block:
        return False
    db.delete(block)
    db.commit()
    return True


def resolve_audience(
    db: Session, group_id: int, channel: str = DEFAULT_CHANNEL
) -> list[RecipientDB]:
    """The group's live audience:
        ((∪ include blocks) − (∪ exclude blocks)) ∪ (manual member pins)
    then re-gated to consenting recipients.

    Precedence (decided 2026-07-26): a manual pin is a deliberate override and
    is **always included** — exclude blocks shape the rule-driven audience but
    never remove a hand-pinned recipient (pins are unioned *after* excludes are
    subtracted). The **consent floor is the one exception**: a non-consenting
    recipient is dropped even if pinned (legal, non-negotiable). Hard
    suppression (bounces/opt-outs) belongs on the consent/suppression floor, not
    in a regular exclude block, so it stays hard against pins too.

    **The consent floor is per channel**, and the caller must say which.
    Consent is keyed `(recipient, brand, channel, purpose)` (ADR-163 point 1),
    so gating a push send on email consent asks the wrong question twice over:
    it would admit people who accepted email and never accepted notifications,
    and refuse people who did the reverse. It defaulted to email while email
    was the only channel, which made a push send unplannable — the audience
    resolved to nobody and the planner reported "0 consenting recipients".

    The default stays email for the screens that are previewing an email
    audience; the send path passes the variant's channel."""
    # The brand comes from the GROUP, never from the caller's working context.
    # A group belongs to exactly one brand (ADR-150 point 2), so resolving it
    # gates on that brand's consent — and a manager who switched brand between
    # building a send and firing it cannot change whose consent was checked.
    # Same reasoning as `brand_for_snapshot` on the delivery side.
    group = group_regardless_of_brand(db, group_id)
    if group is None:
        return []
    brand_id = group.brand_id

    # The group's brand, not the caller's — so the blocks read here are the
    # ones that belong to the group being resolved.
    blocks = list_blocks(db, group_id, brand_id=brand_id)

    include_ids: set[int] = set()
    exclude_ids: set[int] = set()
    for block in blocks:
        ids = {r.id for r in _recipients_for_criteria(db, block.criteria, brand_id)}
        if block.kind == "exclude":
            exclude_ids |= ids
        else:
            include_ids |= ids

    # Excludes subtract from the rule-driven set only; manual pins are then
    # unioned back in so they survive excludes ("always included", except
    # consent below). "keep both" — hand-picked recipients alongside the rules.
    final_ids = (include_ids - exclude_ids) | get_member_recipient_ids(
        db, group_id, brand_id=brand_id
    )
    if not final_ids:
        return []

    records = (
        db.query(RecipientDB)
        .filter(
            RecipientDB.id.in_(final_ids),
            # Consent floor, for THIS brand AND this channel.
            is_consenting_filter(brand_id, channel),
        )
        .order_by(RecipientDB.id.asc())
        .all()
    )
    return records


# ---------------------------------------------------------------------------
# System-suggested audience — content/category driven (use case 1)
# ---------------------------------------------------------------------------

def _brand_of_campaign(db: Session, campaign_id: int) -> int:
    """The brand a campaign belongs to, for gating its suggested audience.

    A suggestion counts how many people a block would reach, and that count is
    only meaningful against the consent of the brand the campaign will send as.
    Counting against every brand's consent would advertise reach the send
    cannot deliver.
    """
    from app.campaigns.db_models import CampaignDB

    brand_id = (
        db.query(CampaignDB.brand_id).filter(CampaignDB.id == campaign_id).scalar()
    )
    if brand_id is None:
        raise ValueError(
            f"Campaign {campaign_id} has no brand, so the consent to gate its "
            "suggested audience on is unknown. Refusing rather than guessing."
        )
    return brand_id


def campaign_category_scores(db: Session, campaign_id: int) -> list[dict]:
    """Category weights across **every variant** of the campaign, whatever its
    channel — decided 2026-09-18 after the user asked whether suggestion should
    check channels.

    Kept channel-blind because [[ADR-160 — Channel Model and Composition]]
    point 7 makes the campaign the *topic* and the channel a delivery
    preference: a push variant of a hiking campaign is still about hiking, so
    the audience it suggests is a hiking audience. The per-channel truth is
    delivered where it changes a decision — the resolved count on the send
    form, which differs per channel from the same group.

    **The accepted cost:** a campaign whose push content is narrower than its
    email content suggests a broader audience than that push needs. The manager
    edits the blocks, which the suggestion is explicitly a proposal for rather
    than a locked list.
    """
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
            "count": count_for_criteria(db, criteria, _brand_of_campaign(db, campaign_id)),
        })
    return suggestions


def create_suggested_group_for_campaign(db: Session, campaign_id: int, campaign_name: str) -> AudienceGroupDB:
    """Materialize a new group seeded with the campaign's suggested include
    blocks. Blocks are marked source='suggested' so the UI can badge them as the
    system's proposal — fully editable/deletable, never a locked list."""
    # The group belongs to the campaign's brand, not to whoever clicked. Same
    # rule as everywhere else a brand is needed: derive it, never read it off
    # the viewer's context.
    brand_id = _brand_of_campaign(db, campaign_id)

    base_name = f"{campaign_name} — suggested audience"
    name = base_name
    suffix = 2
    # Scoped to the brand, because the constraint is (brand_id, lower(name)).
    # Querying every brand would enforce a stricter rule than the database and
    # push brand B's group to "(2)" because brand A happens to own the name —
    # the wrong direction entirely for a per-brand scope.
    while (
        db.query(AudienceGroupDB)
        .filter(
            AudienceGroupDB.brand_id == brand_id,
            func.lower(AudienceGroupDB.name) == name.lower(),
        )
        .first()
    ):
        name = f"{base_name} ({suffix})"
        suffix += 1
        # `audience_groups.name` is String(255) and a long campaign name plus a
        # suffix can exceed it, which would fail as a database error rather
        # than as the collision it actually is.
        if len(name) > 255:
            name = f"{base_name[:240].rstrip()} ({suffix})"

    group = create_group(
        db,
        name,
        brand_id,
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
            brand_id=brand_id,
        )
    return group


def recalculate_suggested_blocks(
    db: Session, group_id: int, *, brand_id: int
) -> AudienceGroupDB | None:
    """Re-derive a group's suggested include blocks from its source campaign's
    *current* content — for after a manager adjusts slots/content. Applies only
    the delta so nothing else is disturbed:
      • categories the campaign no longer covers → their suggested block removed
      • categories newly covered → a fresh suggested block added
      • a surviving category's suggested block is left untouched, preserving any
        threshold the manager already tuned on it
    Manual blocks and manual member pins are never touched. Returns None if the
    group has no source campaign to recalculate against."""
    group = get_group(db, group_id, brand_id=brand_id)
    if not group or not group.source_campaign_id:
        return None

    desired = suggest_include_blocks_for_campaign(db, group.source_campaign_id)
    desired_by_cat = {s["criteria"]["category_id"]: s for s in desired}

    existing_suggested = [
        b for b in list_blocks(db, group_id, brand_id=brand_id)
        if b.source == "suggested"
    ]
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
                brand_id=brand_id,
            )
            added += 1

    return group
