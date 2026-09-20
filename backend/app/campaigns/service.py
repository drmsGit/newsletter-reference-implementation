from sqlalchemy import func
from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
from app.campaigns.models import Campaign, CampaignWithVariants, Variant, ModuleInstance, DecisionSlot, DecisionResolution
from app.channels.registry import get_channel, max_modules_for
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.modules.registry import envelope_module_type, get_manifest
from app.recipients.db_models import RecipientDB


def brand_of_variant(db: Session, variant_id: int) -> int | None:
    """The brand a variant belongs to, via its campaign (ADR-172 point 5).

    A **resolver**, not a scoped getter, and the distinction matters. A scoped
    getter answers "give me this row if it is in my brand" and is how a request
    addresses something. This answers "which brand does this row belong to",
    which is what an internal caller holding a variant id and no request needs
    — the same question `_brand_of_campaign` (`audience/service.py`) and
    `sending_brand_id` (`decision/strategies/base.py`) already ask, in their own
    corners, by walking the same two joins.

    Returns `None` when the chain is broken. The caller must not read that as
    "every brand": an unknown brand is not a wildcard, and ADR-150 point 8 is
    explicit that widening is a deliberate act.
    """
    return (
        db.query(CampaignDB.brand_id)
        .join(VariantDB, VariantDB.campaign_id == CampaignDB.id)
        .filter(VariantDB.id == variant_id)
        .scalar()
    )


# --- scoped getters (ADR-172 point 5) ---------------------------------------
#
# Nothing below `campaigns` carries a `brand_id` of its own, and none of them
# should: ADR-150's addendum settles that a child is per-brand transitively,
# and point 5 refuses new columns on that reasoning. So the chain is walked in
# the **selecting** query rather than checked after it — a row outside the
# brand is not found, so there is no moment where it is in hand and something
# still has to remember to refuse it.
#
# Measured before they were written (ADR-172's 2026-09-20 addendum): all three
# hops land on primary keys, and the deepest chain costs eight buffers.


def get_variant(db: Session, variant_id: int, *, brand_id: int) -> VariantDB | None:
    """One variant, if it belongs to this brand. Otherwise None."""
    return (
        db.query(VariantDB)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(VariantDB.id == variant_id, CampaignDB.brand_id == brand_id)
        .first()
    )


def get_module(db: Session, module_id: int, *, brand_id: int) -> ModuleInstanceDB | None:
    """One module instance, via `module -> variant -> campaign -> brand`."""
    return (
        db.query(ModuleInstanceDB)
        .join(VariantDB, VariantDB.id == ModuleInstanceDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(ModuleInstanceDB.id == module_id, CampaignDB.brand_id == brand_id)
        .first()
    )


def get_decision_slot(db: Session, slot_id: int, *, brand_id: int) -> DecisionSlotDB | None:
    """One decision slot, via `slot -> variant -> campaign -> brand`."""
    return (
        db.query(DecisionSlotDB)
        .join(VariantDB, VariantDB.id == DecisionSlotDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(DecisionSlotDB.id == slot_id, CampaignDB.brand_id == brand_id)
        .first()
    )


def get_campaign(db: Session, campaign_id: int, *, brand_id: int) -> CampaignDB | None:
    """One campaign, within a brand. The root of every chain above."""
    return (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id, CampaignDB.brand_id == brand_id)
        .first()
    )


def to_campaign(record: CampaignDB) -> Campaign:
    return Campaign(
        id=record.id,
        name=record.name,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def to_variant(record: VariantDB, db: Session) -> Variant:
    """Project a variant, reading its envelope copy from the module that holds
    it (ADR-162 point 1).

    **The session is required**, which is the honest cost of the move: this was
    a pure row-to-model mapper, and a field that lives in another table gives
    it a query. It was optional during the expand half so a caller without a
    session could still fall back to the columns; the columns are gone, so
    there is nothing to fall back to and a caller that cannot query cannot
    answer.
    """
    from app.rendering.service import envelope_fields_for_variant

    envelope = envelope_fields_for_variant(db, record.id, record.channel)

    return Variant(
        id=record.id,
        campaign_id=record.campaign_id,
        channel=record.channel,
        name=record.name,
        subject=envelope.get("subject"),
        preheader=envelope.get("preheader"),
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_campaigns(db: Session, *, brand_id: int) -> list[Campaign]:
    """Campaigns, scoped to one brand (ADR-150 point 2).

    **`brand_id=None` means every brand, and is not the caller's default.**
    It exists for the places that genuinely span brands — a platform-wide
    count, a migration, a test. Any surface a user looks at must pass the
    working brand, because ADR-150 point 2 makes the switcher a hard boundary,
    not a preference.
    """
    return [
        to_campaign(record)
        for record in db.query(CampaignDB)
        .filter(CampaignDB.brand_id == brand_id)
        .all()
    ]


def list_all_campaigns(db: Session) -> list[Campaign]:
    """Every campaign, across every brand — the ADR-172 point 4 escape hatch.

    For the callers that legitimately have no working brand: platform counts,
    migrations, seeds. Counted by `test_brand_boundary.py`, and no router may
    reach for it, because every request has a brand.
    """
    return [to_campaign(record) for record in db.query(CampaignDB).all()]


def create_campaign(
    db: Session,
    name: str,
    brand_id: int,
    channel: str,
    status: str = "draft",
    initial_variant_name: str = "Variant A",
) -> CampaignWithVariants:
    """Create a campaign and the one variant it must always have.

    **`channel` is required and has no default, even though this reads like a
    campaign-level argument.** It is not one — ADR-160 point 4 keeps channel off
    the campaign entirely; what needs it is the initial variant this function
    manufactures to satisfy the always-has-a-variant invariant. Defaulting it to
    email would mean a caller that never thought about channel silently produces
    an email variant, which is harmless exactly until it is not.
    """
    # A campaign must always have a variant (invariant) — flush (not commit)
    # after the campaign insert so campaign.id is assigned without ending
    # the transaction, then commit both inserts atomically in one go. A
    # failure between them can no longer leave a persisted campaign with
    # zero variants.
    campaign = CampaignDB(
        name=name,
        status=status,
        brand_id=brand_id,
    )

    db.add(campaign)
    db.flush()

    initial_variant = VariantDB(
        campaign_id=campaign.id,
        channel=channel,
        name=initial_variant_name,
        status="draft",
    )

    db.add(initial_variant)
    db.commit()
    db.refresh(campaign)
    db.refresh(initial_variant)

    return CampaignWithVariants(
        **to_campaign(campaign).model_dump(),
        variants=[to_variant(initial_variant, db)],
    )


def list_variants_for_campaign(
    db: Session,
    campaign_id: int,
    *,
    brand_id: int,
) -> list[Variant]:
    records = (
        db.query(VariantDB)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(VariantDB.campaign_id == campaign_id, CampaignDB.brand_id == brand_id)
        .all()
    )

    return [to_variant(record, db) for record in records]


def create_variant_for_campaign(
    db: Session,
    campaign_id: int,
    name: str,
    channel: str,
    subject: str | None = None,
    preheader: str | None = None,
    status: str = "draft",
    *,
    brand_id: int,
) -> Variant:
    """Add a variant. **The channel is chosen here and never again** (ADR-160
    point 5): switching an email variant to push would invalidate its modules,
    its content-readiness and its renderer at once, so changing channel means
    creating a new variant. `update_variant` therefore does not touch it.

    `subject` and `preheader` are email-shaped and stay on the row for now —
    ADR-162 point 1 moves them into a `header` module and is not built. A push
    variant leaves them NULL.
    """
    # The parent is resolved within the brand before anything is written, so a
    # variant cannot be hung off another brand's campaign (ADR-172 point 5).
    if get_campaign(db, campaign_id, brand_id=brand_id) is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    variant = VariantDB(
        campaign_id=campaign_id,
        channel=channel,
        name=name,
        status=status,
    )

    db.add(variant)
    db.commit()
    db.refresh(variant)

    # Into the module that declares them, not onto the row (ADR-162 point 1).
    # The columns still exist and are deliberately no longer written: two
    # places holding the same field is the failure mode that point rejects,
    # and the read path stopped preferring the columns before this did.
    set_envelope_fields(
        db, variant.id, {"subject": subject, "preheader": preheader},
        brand_id=brand_id,
    )
    return to_variant(variant, db)


def update_variant(
    db: Session,
    variant_id: int,
    name: str,
    subject: str | None = None,
    preheader: str | None = None,
    *,
    brand_id: int,
) -> Variant | None:
    variant = get_variant(db, variant_id, brand_id=brand_id)
    if variant is None:
        return None
    variant.name = name
    db.commit()
    set_envelope_fields(
        db, variant.id, {"subject": subject, "preheader": preheader},
        brand_id=brand_id,
    )
    db.refresh(variant)
    return to_variant(variant, db)


def to_module_instance(record: ModuleInstanceDB) -> ModuleInstance:
    return ModuleInstance(
        id=record.id,
        variant_id=record.variant_id,
        module_type=record.module_type,
        position=record.position,
        content_record_id=record.content_record_id,
        module_data=record.module_data,
        decision_slot_id=record.decision_slot_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_modules_for_variant(
    db: Session,
    variant_id: int,
    *,
    brand_id: int,
) -> list[ModuleInstance]:
    records = (
        db.query(ModuleInstanceDB)
        .join(VariantDB, VariantDB.id == ModuleInstanceDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(
            ModuleInstanceDB.variant_id == variant_id,
            CampaignDB.brand_id == brand_id,
        )
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    return [to_module_instance(record) for record in records]


def set_envelope_fields(
    db: Session, variant_id: int, fields: dict, *, brand_id: int
) -> None:
    """Write this variant's envelope copy into the module that declares it.

    ADR-162 point 1: subject and preheader are fields of an email, so they live
    in the composition. This is the write half — `envelope_fields_for_variant`
    is the read half, and neither of them names the module.

    **Upserted at position 0** so the envelope module is always first, which is
    where the ADR puts it and what keeps the preheader span at the top of the
    body. Position 0 is free on every variant because
    `create_module_for_variant` appends from 1.

    Bypasses `create_module_for_variant` deliberately: that function appends,
    and this one has a fixed slot. It also must not be refused by the
    cardinality check — an envelope module is not a content module, and a push
    variant is unaffected because push declares no envelope fields at all.
    """
    variant = get_variant(db, variant_id, brand_id=brand_id)
    if variant is None:
        return
    module_type = envelope_module_type(variant.channel)
    if module_type is None:
        # This channel has no envelope. Nothing to write, and nothing was lost
        # — a push has no subject line by construction.
        return

    manifest = get_manifest(variant.channel, module_type)
    allowed = {var.name for var in manifest.variables if var.envelope}
    # Only what the manifest declares, and only what has a value. An empty
    # string would read as "authored and left blank", which is a different
    # claim from "never written".
    data = {k: v for k, v in fields.items() if k in allowed and v}

    existing = (
        db.query(ModuleInstanceDB)
        .filter(
            ModuleInstanceDB.variant_id == variant_id,
            ModuleInstanceDB.module_type == module_type,
        )
        .first()
    )

    if not data:
        # Everything cleared: remove the module rather than keep an empty one.
        if existing is not None:
            db.delete(existing)
            db.commit()
        return

    if existing is None:
        db.add(ModuleInstanceDB(
            variant_id=variant_id,
            module_type=module_type,
            position=0,
            module_data=data,
        ))
    else:
        existing.module_data = data
    db.commit()


def create_module_for_variant(
    db: Session,
    variant_id: int,
    module_type: str,
    content_record_id: int | None = None,
    module_data: dict | None = None,
    decision_slot_id: int | None = None,
    *,
    brand_id: int,
) -> ModuleInstance:
    """Append a module to a variant, within what its channel permits.

    **The channel is derived from the variant, never passed.** Same rule the
    brand work settled on: a caller that can state the channel is a caller that
    can state the wrong one, and the variant already knows (ADR-160 point 4).
    """
    if content_record_id is not None and decision_slot_id is not None:
        raise ValueError(
            "A module cannot have both content_record_id and decision_slot_id set — "
            "rendering would silently prefer content_record_id and ignore the decision slot"
        )

    variant = get_variant(db, variant_id, brand_id=brand_id)
    if variant is None:
        raise ValueError(f"variant {variant_id} does not exist")

    channel = get_channel(variant.channel)
    channel_label = channel.label if channel else variant.channel

    # (1) The module must belong to this channel. ADR-161 point 7: a channel is
    # "an attribute on the variant plus **which manifests it accepts**". The
    # composer's dropdown is already scoped, but a dropdown is not a control —
    # a hand-crafted POST never sees it, and this is the same shape of hole the
    # channel-availability check closes one level up.
    if get_manifest(variant.channel, module_type) is None:
        raise ValueError(
            f"'{module_type}' is not a {channel_label} module, so nothing could "
            f"render it. Each channel accepts only its own modules."
        )

    # (2) Cardinality — ADR-161 point 7's one genuinely channel-level fact, and
    # what keeps ADR-160 point 2's promise that push is "one ModuleInstanceDB"
    # **as a declared capability rather than the composition code special-casing
    # push**. Nothing here knows what push is; it reads a number from a file.
    limit = max_modules_for(variant.channel)
    if limit is not None:
        current = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant_id)
            .count()
        )
        if current >= limit:
            raise ValueError(
                f"A {channel_label} variant holds "
                f"{limit} module{'s' if limit != 1 else ''}, and this one already "
                f"does. Replace it, or add another variant."
            )

    max_position = (
        db.query(func.max(ModuleInstanceDB.position))
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .scalar()
    )
    next_position = (max_position or 0) + 1

    module = ModuleInstanceDB(
        variant_id=variant_id,
        module_type=module_type,
        position=next_position,
        content_record_id=content_record_id,
        decision_slot_id=decision_slot_id,
        module_data=module_data,
    )

    db.add(module)
    db.commit()
    db.refresh(module)

    return to_module_instance(module)


def update_module(
    db: Session,
    module_id: int,
    module_type: str,
    content_record_id: int | None = None,
    module_data: dict | None = None,
    decision_slot_id: int | None = None,
    *,
    brand_id: int,
) -> ModuleInstance | None:
    """Update a module's type, content source and static field data in place.
    Position is untouched (reorder via move_module). Same mutual-exclusion
    guard as create — a module cannot bind both a content record and a
    decision slot."""
    if content_record_id is not None and decision_slot_id is not None:
        raise ValueError(
            "A module cannot have both content_record_id and decision_slot_id set — "
            "rendering would silently prefer content_record_id and ignore the decision slot"
        )

    module = get_module(db, module_id, brand_id=brand_id)
    if module is None:
        return None

    module.module_type = module_type
    module.content_record_id = content_record_id
    module.decision_slot_id = decision_slot_id
    module.module_data = module_data

    db.commit()
    db.refresh(module)
    return to_module_instance(module)


def delete_module(db: Session, module_id: int, *, brand_id: int) -> bool:
    """Remove a module from its variant. Positions of the remaining modules are
    left as-is — the (variant_id, position) uniqueness only requires no
    duplicates, not a contiguous sequence, and rendering orders by position, so
    a gap is harmless. Any content overrides on the module go with it (they're
    meaningless once the module is gone)."""
    module = get_module(db, module_id, brand_id=brand_id)
    if module is None:
        return False

    from app.overrides.db_models import ContentOverrideDB

    db.query(ContentOverrideDB).filter(
        ContentOverrideDB.module_instance_id == module_id
    ).delete()
    db.delete(module)
    db.commit()
    return True


def move_module(
    db: Session, module_id: int, direction: str, *, brand_id: int
) -> ModuleInstance | None:
    """Move a module one step up or down within its variant by swapping its
    position with the adjacent module. No-op if already at the top/bottom."""
    if direction not in ("up", "down"):
        raise ValueError("direction must be 'up' or 'down'")

    module = get_module(db, module_id, brand_id=brand_id)
    if module is None:
        return None

    neighbors = db.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.variant_id == module.variant_id
    )
    if direction == "up":
        neighbor = (
            neighbors.filter(ModuleInstanceDB.position < module.position)
            .order_by(ModuleInstanceDB.position.desc())
            .first()
        )
    else:
        neighbor = (
            neighbors.filter(ModuleInstanceDB.position > module.position)
            .order_by(ModuleInstanceDB.position.asc())
            .first()
        )

    if neighbor is None:
        # Already at the top (up) or bottom (down) — nothing to swap with.
        return to_module_instance(module)

    # Swap the two position values via a temporary slot, so the
    # (variant_id, position) unique constraint doesn't trip on a transient
    # duplicate mid-swap. Positions are always >= 1, so -1 is a safe temp.
    module_pos, neighbor_pos = module.position, neighbor.position
    module.position = -1
    db.flush()
    neighbor.position = module_pos
    db.flush()
    module.position = neighbor_pos
    db.commit()
    db.refresh(module)
    return to_module_instance(module)


def _normalize_for_strategy(
    decision_strategy: str,
    candidate_filter: dict | None,
    strategy_config: dict | None,
) -> tuple[dict | None, dict | None]:
    """Resolve the strategy and lock the config/filter to its declared shape.
    Lazy imports keep the decision-strategy registry out of this module's
    import graph. Raises ValueError for an unknown strategy or a config that
    doesn't match the strategy's declared fields."""
    from app.decision.strategies.base import normalize_slot_config
    from app.decision.strategies.registry import get_strategy

    strategy = get_strategy(decision_strategy)
    return normalize_slot_config(strategy.meta, candidate_filter, strategy_config)


def update_decision_slot(
    db: Session,
    slot_id: int,
    decision_strategy: str,
    candidate_filter: dict | None,
    strategy_config: dict | None,
    *,
    brand_id: int,
) -> DecisionSlotDB | None:
    slot = get_decision_slot(db, slot_id, brand_id=brand_id)
    if slot is None:
        return None
    # Lock the config/filter structure to the (possibly newly-chosen) strategy
    # before persisting — no more "accepts any shape for any strategy, only
    # fails at resolution time". Switching strategies re-derives the structure.
    candidate_filter, strategy_config = _normalize_for_strategy(
        decision_strategy, candidate_filter, strategy_config
    )
    slot.decision_strategy = decision_strategy
    slot.candidate_filter = candidate_filter
    slot.strategy_config = strategy_config
    db.commit()
    db.refresh(slot)
    return slot


def to_decision_slot(record: DecisionSlotDB) -> DecisionSlot:
    return DecisionSlot(
        id=record.id,
        variant_id=record.variant_id,
        name=record.name,
        decision_type=record.decision_type,
        decision_strategy=record.decision_strategy,
        candidate_filter=record.candidate_filter,
        strategy_config=record.strategy_config,
        max_results=record.max_results,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_decision_slots_for_variant(
    db: Session,
    variant_id: int,
    *,
    brand_id: int,
) -> list[DecisionSlot]:
    records = (
        db.query(DecisionSlotDB)
        .join(VariantDB, VariantDB.id == DecisionSlotDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(
            DecisionSlotDB.variant_id == variant_id,
            CampaignDB.brand_id == brand_id,
        )
        .all()
    )

    return [to_decision_slot(record) for record in records]


def create_decision_slot_for_variant(
    db: Session,
    variant_id: int,
    name: str,
    decision_type: str = "content_recommendation",
    decision_strategy: str = "top_score",
    candidate_filter: dict | None = None,
    strategy_config: dict | None = None,
    max_results: int = 1,
    *,
    brand_id: int,
) -> DecisionSlot:
    # The parent is resolved within the brand before the slot is written, the
    # same guard `create_variant_for_campaign` takes one level up.
    if get_variant(db, variant_id, brand_id=brand_id) is None:
        raise ValueError(f"variant {variant_id} does not exist")

    candidate_filter, strategy_config = _normalize_for_strategy(
        decision_strategy, candidate_filter, strategy_config
    )
    slot = DecisionSlotDB(
        variant_id=variant_id,
        name=name,
        decision_type=decision_type,
        decision_strategy=decision_strategy,
        candidate_filter=candidate_filter,
        strategy_config=strategy_config,
        max_results=max_results,
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)

    return to_decision_slot(slot)


def to_decision_resolution(record: DecisionResolutionDB) -> DecisionResolution:
    return DecisionResolution(
        id=record.id,
        decision_slot_id=record.decision_slot_id,
        recipient_id=record.recipient_id,
        content_record_id=record.content_record_id,
        content_version_id=record.content_version_id,
        reason=record.reason,
        score=record.score,
        created_at=record.created_at,
    )


def create_decision_resolution(
    db: Session,
    decision_slot_id: int,
    content_record_id: int,
    content_version_id: int | None = None,
    recipient_id: int | None = None,
    reason: str | None = None,
    score: float | None = None,
    *,
    brand_id: int,
) -> DecisionResolution:
    # No orphan row should ever be silently accepted, regardless of whether
    # the DB engine happens to enforce FK constraints — validate referenced
    # IDs exist before insert rather than only failing later at rendering's
    # join-based lookup.
    # **Both parents are resolved within the brand**, not merely proved to
    # exist. A resolution binds a slot to a content record, and ADR-013's
    # addendum is explicit that across a brand boundary that reference cannot
    # be expressed at all — so "exists" was never the question worth asking.
    if get_decision_slot(db, decision_slot_id, brand_id=brand_id) is None:
        raise ValueError(f"DecisionSlot {decision_slot_id} not found")

    if db.query(ContentRecordDB.id).filter(
        ContentRecordDB.id == content_record_id,
        ContentRecordDB.brand_id == brand_id,
    ).first() is None:
        raise ValueError(f"ContentRecord {content_record_id} not found")

    if content_version_id is not None:
        if db.query(ContentVersionDB.id).filter(ContentVersionDB.id == content_version_id).first() is None:
            raise ValueError(f"ContentVersion {content_version_id} not found")

    if recipient_id is not None:
        if db.query(RecipientDB.id).filter(RecipientDB.id == recipient_id).first() is None:
            raise ValueError(f"Recipient {recipient_id} not found")

    resolution = DecisionResolutionDB(
        decision_slot_id=decision_slot_id,
        recipient_id=recipient_id,
        content_record_id=content_record_id,
        content_version_id=content_version_id,
        reason=reason,
        score=score,
    )

    db.add(resolution)
    db.commit()
    db.refresh(resolution)

    return to_decision_resolution(resolution)


def list_resolutions_for_decision_slot(
    db: Session,
    decision_slot_id: int,
    *,
    brand_id: int,
) -> list[DecisionResolution]:
    records = (
        db.query(DecisionResolutionDB)
        .join(DecisionSlotDB, DecisionSlotDB.id == DecisionResolutionDB.decision_slot_id)
        .join(VariantDB, VariantDB.id == DecisionSlotDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(
            DecisionResolutionDB.decision_slot_id == decision_slot_id,
            CampaignDB.brand_id == brand_id,
        )
        .all()
    )

    return [to_decision_resolution(record) for record in records]


