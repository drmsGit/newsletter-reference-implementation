from datetime import datetime

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
from app.campaigns.models import Campaign, CampaignWithVariants, Variant, ModuleInstance, DecisionSlot, DecisionResolution
from app.channels.registry import get_channel, max_modules_for
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.modules.registry import envelope_module_type, get_manifest, hideable_fields
from app.recipients.db_models import RecipientDB


class ChannelUnavailable(ValueError):
    """The requested channel is not enabled in this deployment.

    **A `ValueError` subclass on purpose.** Both routers already catch
    `ValueError` from these functions, so this stays caught by everything that
    caught it before — but a route that wants to answer 400 rather than 404 can
    name it. Without the distinction, "this campaign is not in your brand" and
    "that channel is switched off" arrive as the same exception and get the
    same status code, and one of the two answers is then a lie.
    """


def _refuse_unavailable_channel(db: Session, channel: str) -> None:
    """Refuse a channel this deployment has not enabled (ADR-160 point 8).

    Two gates inside `channel_available`, and both matter: the channel must
    exist on disk at all, and this deployment must not have switched it off.

    **Raises rather than returning a bool**, because every caller's correct
    response is the same one and a bool is a thing a caller can ignore — which
    is precisely how the JSON routers came to ignore it. `ValueError` rather
    than an HTTP error, so the service stays unaware of which plane called it;
    both routers already map `ValueError` from these functions.
    """
    from app.channels.registry import load_error
    from app.settings.service import channel_available

    if not channel_available(db, channel):
        # A broken manifest and an absent one used to read the same (task-20).
        broken = load_error(channel)
        if broken:
            raise ChannelUnavailable(
                f"'{channel}' is declared, but its manifest could not be read "
                f"({broken}). Fix storage/channels/{channel}.json."
            )
        raise ChannelUnavailable(
            f"'{channel}' is not an available channel in this deployment."
        )


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
        envelope=envelope,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def page_campaigns(db: Session, params, *, brand_id: int, q: str | None = None):
    """One ADR-185 page of the brand's campaigns, newest first, narrowed by name.

    No status filter, deliberately: `CampaignDB.status` is set at creation and
    nothing moves it (task-216), so it would sort every campaign into 'draft'.
    Where a campaign stands is the monitoring read model's answer."""
    from app.pagination import page_of_query

    query = db.query(CampaignDB).filter(CampaignDB.brand_id == brand_id)
    if (q or "").strip():
        query = query.filter(CampaignDB.name.icontains(q.strip(), autoescape=True))
    return page_of_query(query, params, CampaignDB.created_at.desc(), CampaignDB.id.desc(),
                         convert=to_campaign)


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
    # **ADR-160 point 8, enforced here rather than in a form.** A channel this
    # deployment has not turned on is "refused server-side if requested
    # directly", not merely absent from a dropdown. Until 2026-09-20 the check
    # lived at the two `app/frontend/router.py` call sites and nowhere else, so
    # the JSON plane created campaigns on disabled channels without complaint —
    # and retiring the Jinja UI would have deleted the enforcement rather than
    # moved it.
    #
    # Before anything is written, so a refusal leaves no row behind.
    _refuse_unavailable_channel(db, channel)

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


#: The whole vocabulary of `variants.status` (task-203; Variant Editor design
#: interview Q4.6). `ready` is the manager's assertion that the variant is done,
#: which the variant list reads instead of recomputing completeness. `approved`
#: belongs to the send, `sent` to send instances, `archived` to the
#: data-lifecycle ADR. Enforced here, as `CONTENT_STATUSES` is; existing rows
#: are not rewritten.
VARIANT_STATUSES = ("draft", "ready")


def create_variant_for_campaign(
    db: Session,
    campaign_id: int,
    name: str,
    channel: str,
    envelope: dict | None = None,
    status: str = "draft",
    *,
    brand_id: int,
) -> Variant:
    """Add a variant. **The channel is chosen here and never again** (ADR-160
    point 5): switching an email variant to push would invalidate its modules,
    its content-readiness and its renderer at once, so changing channel means
    creating a new variant. `update_variant` therefore does not touch it.

    `envelope` holds the channel's envelope fields by name — email's subject
    and preheader — which are not columns of the variant: `set_envelope_fields`
    below writes them into the variant's envelope module (ADR-162 point 1;
    migration 0011 moved them there and 0012 dropped the columns). Push
    declares no envelope fields, so a push variant has none.
    """
    # The parent is resolved within the brand before anything is written, so a
    # variant cannot be hung off another brand's campaign (ADR-172 point 5).
    if get_campaign(db, campaign_id, brand_id=brand_id) is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    if status not in VARIANT_STATUSES:
        raise ValueError(
            f"Unknown variant status '{status}'. Expected one of: {', '.join(VARIANT_STATUSES)}"
        )

    # ADR-160 point 8 again, and this is the call site that matters most: the
    # channel belongs to the variant (point 4) and is fixed at creation (point
    # 5), so this is the only moment it can be refused at all.
    _refuse_unavailable_channel(db, channel)

    variant = VariantDB(
        campaign_id=campaign_id,
        channel=channel,
        name=name,
        status=status,
    )

    db.add(variant)
    db.commit()
    db.refresh(variant)

    # Into the module that declares them, not onto the row (ADR-162 point 1):
    # the variant has no such columns since migration 0012, and two places
    # holding the same field is the failure mode that point rejects.
    set_envelope_fields(db, variant.id, envelope or {}, brand_id=brand_id)
    return to_variant(variant, db)


class StaleWrite(Exception):
    """A write based on an out-of-date read (task-110, ADR-180 point 2).

    **Deliberately not a ValueError**, like `BrokenCampaignChain`: every
    composer route turns ValueError into a 400 "your request is wrong", and
    this is "your request was right when you read, and someone has since
    changed it" — a 409.
    """


def refuse_stale(db: Session, row, expected_updated_at: datetime | None, label: str) -> None:
    """Refuse the write when the caller's token no longer matches the row.

    `updated_at` is the version token (ADR-180 point 2). The row is re-read
    `FOR UPDATE`, so a second writer waits here until the first commits and
    then compares against the first's timestamp, rather than both passing the
    check and the later one winning. No token means no check: the token is
    optional (user, 2026-10-03), which keeps the Jinja forms and existing
    integrations working unchanged while the React editor always sends it.
    """
    if expected_updated_at is None:
        return
    db.refresh(row, with_for_update=True)
    if row.updated_at != expected_updated_at:
        raise StaleWrite(
            f"This {label} was changed at {row.updated_at.isoformat()}, after you "
            f"loaded it. Reload it and apply your change again."
        )


def update_variant(
    db: Session,
    variant_id: int,
    name: str,
    envelope: dict | None = None,
    *,
    brand_id: int,
    expected_updated_at: datetime | None = None,
) -> Variant | None:
    """Rename the variant and, when `envelope` is given, replace its envelope
    copy. `None` leaves the envelope as it is: renaming is not clearing."""
    variant = get_variant(db, variant_id, brand_id=brand_id)
    if variant is None:
        return None
    refuse_stale(db, variant, expected_updated_at, "variant")
    variant.name = name
    # Moved by hand: the envelope lives in the header module, so an edit to it
    # alone leaves this row clean and `onupdate` never fires — two editors
    # changing the subject would never conflict (task-110).
    variant.updated_at = func.now()
    db.commit()
    if envelope is not None:
        set_envelope_fields(db, variant.id, envelope, brand_id=brand_id)
    db.refresh(variant)
    return to_variant(variant, db)


def module_audit_detail(module) -> dict:
    """What a module.created / module.updated entry records (task-252), the
    same on both planes. Takes the row or its response model. `module_data` is
    left out: it is the module's copy, edited field by field, and the entry
    records what the module is and what it is bound to."""
    return {
        "variant_id": module.variant_id, "module_type": module.module_type,
        "content_record_id": module.content_record_id,
        "decision_slot_id": module.decision_slot_id,
    }


def slot_audit_detail(slot) -> dict:
    """What a decision_slot.created / .updated entry records (task-252)."""
    return {
        "variant_id": slot.variant_id, "name": slot.name,
        "decision_strategy": slot.decision_strategy,
        "candidate_filter": slot.candidate_filter, "strategy_config": slot.strategy_config,
    }


def to_module_instance(record: ModuleInstanceDB) -> ModuleInstance:
    return ModuleInstance(
        id=record.id,
        variant_id=record.variant_id,
        module_type=record.module_type,
        position=record.position,
        content_record_id=record.content_record_id,
        module_data=record.module_data,
        decision_slot_id=record.decision_slot_id,
        hidden_fields=list(record.hidden_fields or []),
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
    # claim from "never written". Trimmed here rather than by each caller:
    # only the Jinja forms used to, so " " arrived over JSON as a subject
    # (task-250), and this is the one place every path writes through.
    trimmed = {k: v.strip() if isinstance(v, str) else v for k, v in fields.items()}
    data = {k: v for k, v in trimmed.items() if k in allowed and v}

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
    _refuse_foreign_binding(
        db, variant_id, content_record_id, decision_slot_id, brand_id=brand_id
    )

    channel = get_channel(variant.channel)
    channel_label = channel.label if channel else variant.channel

    # (1) The module must belong to this channel, and not be its envelope.
    _refuse_module_type(variant.channel, module_type)
    _refuse_module_data(variant.channel, module_type, module_data)

    # (2) Cardinality — ADR-161 point 7's one genuinely channel-level fact, and
    # what keeps ADR-160 point 2's promise that push is "one ModuleInstanceDB"
    # **as a declared capability rather than the composition code special-casing
    # push**. Nothing here knows what push is; it reads a number from a file.
    # The envelope module is not counted, as the composition read does not
    # count it: it is the email's header, not one of its modules (task-249).
    limit = max_modules_for(variant.channel)
    if limit is not None:
        envelope_type = envelope_module_type(variant.channel)
        current = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant_id)
            .filter(ModuleInstanceDB.module_type != envelope_type if envelope_type else True)
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


class ModuleDataInvalid(ValueError):
    """Module data with fields its manifest does not declare, or values that
    are not text (task-253). Carries every bad field at once, so a form can
    mark each; a `ValueError`, so a caller that shows the message as a whole
    (the Jinja forms) needs nothing new."""

    def __init__(self, errors: list[tuple[str, str]]):
        self.errors = errors
        super().__init__("; ".join(f"{field}: {message}" for field, message in errors))


def _refuse_module_data(channel_key: str, module_type: str, module_data: dict | None) -> None:
    """`module_data` holds only the manifest's fields, each as text or empty.

    The same rule overrides apply to their keys (`overrides/service.py`), now
    applied to the module's own copy. What stays allowed is deliberate:
    ADR-177 keeps `required` and lengths advisory while editing — completeness
    is shown in the editor (Variant Editor interview 2.2) — so a missing field,
    a None, or a long value is accepted. Every field type `fields.json`
    declares today (text, richtext, url) is a string; a URL is not checked for
    shape, for the same reason a length is not.
    """
    if not module_data:
        return
    manifest = get_manifest(channel_key, module_type)
    # A catalogue module keeps only the fields it types itself; its content
    # fields come from the record or the slot, never from module_data (ADR-179's
    # 2026-10-04 addendum). A static module's fields are all its own.
    declared = {
        variable.name for variable in manifest.variables
        if not manifest.cms or variable.source == "module"
    } if manifest else set()
    errors = []
    for field, value in module_data.items():
        if field not in declared:
            errors.append((field, f"'{module_type}' has no field '{field}'"))
        elif value is not None and not isinstance(value, str):
            errors.append((field, f"'{field}' must be text, not {type(value).__name__}"))
    if errors:
        raise ModuleDataInvalid(errors)


def _refuse_module_type(channel_key: str, module_type: str) -> None:
    """A module's type must be one its channel accepts, and not the envelope.

    ADR-161 point 7: a channel is "an attribute on the variant plus **which
    manifests it accepts**". The composer's dropdown is already scoped, but a
    dropdown is not a control — a hand-crafted request never sees it, and this
    is the same shape of hole the channel-availability check closes one level
    up. Checked on create and, since task-249, on update too: an update used to
    overwrite the type unchecked.

    The envelope module (email's header) is refused here because subject and
    preheader are written through the variant (`set_envelope_fields`,
    ADR-162 point 1), which keeps exactly one of it, first. One added as an
    ordinary module lands at the end, where nothing reads it.
    """
    channel = get_channel(channel_key)
    channel_label = channel.label if channel else channel_key
    if get_manifest(channel_key, module_type) is None:
        raise ValueError(
            f"'{module_type}' is not a {channel_label} module, so nothing could "
            f"render it. Each channel accepts only its own modules."
        )
    if module_type == envelope_module_type(channel_key):
        raise ValueError(
            f"'{module_type}' carries the subject and preheader. Set those on the "
            f"variant; it keeps the one {module_type} module itself."
        )


def _refuse_foreign_binding(
    db: Session,
    variant_id: int,
    content_record_id: int | None,
    decision_slot_id: int | None,
    *,
    brand_id: int,
) -> None:
    """A module binds its own brand's content and its own variant's slot (task-248).

    The variant or module is already selected within the brand; the ids it is
    being bound to were not, and rendering loads a bound record by id alone.
    So a record from another brand would be previewed, snapshotted and sent
    under this one (ADR-150 point 8). A record outside the brand is "not
    found", as `get_content_record` treats it, rather than named as foreign.
    A slot must hang off this very variant: slots are per-variant layout
    (ADR-083), and one on another variant would resolve that variant's picks.
    """
    from app.content.service import get_content_record

    if content_record_id is not None and get_content_record(
        db, content_record_id, brand_id=brand_id
    ) is None:
        raise ValueError(f"Content record {content_record_id} not found")
    if decision_slot_id is not None and (
        db.query(DecisionSlotDB.id)
        .filter(DecisionSlotDB.id == decision_slot_id, DecisionSlotDB.variant_id == variant_id)
        .first()
        is None
    ):
        raise ValueError(f"Decision slot {decision_slot_id} is not on this variant")


def update_module(
    db: Session,
    module_id: int,
    module_type: str,
    content_record_id: int | None = None,
    module_data: dict | None = None,
    decision_slot_id: int | None = None,
    *,
    brand_id: int,
    expected_updated_at: datetime | None = None,
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
    refuse_stale(db, module, expected_updated_at, "module")
    channel_key = db.get(VariantDB, module.variant_id).channel
    _refuse_module_type(channel_key, module_type)
    _refuse_module_data(channel_key, module_type, module_data)
    _refuse_foreign_binding(
        db, module.variant_id, content_record_id, decision_slot_id, brand_id=brand_id
    )

    if module_type != module.module_type:
        # A hidden list is a layout choice for this module type: a new type
        # keeps only what it still marks hideable (ADR-187). Re-binding the
        # record keeps it whole.
        hideable = set(hideable_fields(get_manifest(channel_key, module_type)))
        module.hidden_fields = [f for f in (module.hidden_fields or []) if f in hideable]
    module.module_type = module_type
    module.content_record_id = content_record_id
    module.decision_slot_id = decision_slot_id
    module.module_data = module_data

    db.commit()
    db.refresh(module)
    return to_module_instance(module)


class NotHideable(Exception):
    """A field the module's manifest does not mark hideable (ADR-187 point 2).
    Carries the names, for a 422 the client can mark per field."""

    def __init__(self, fields: list[str], module_type: str):
        self.fields = fields
        super().__init__(
            f"{', '.join(fields)} cannot be hidden in a {module_type} module: its manifest "
            f"does not mark {'it' if len(fields) == 1 else 'them'} hideable."
        )


def set_hidden_fields(
    db: Session, module_id: int, fields: list[str], *, brand_id: int,
    expected_updated_at: datetime | None = None,
) -> tuple[ModuleInstance, list[str]] | None:
    """Make a module's hidden fields exactly `fields` (ADR-187), returning the
    module and the list it had, or None when the module is not in this brand.

    Who may call this is the route's question: people only, in both
    directions. Every name must be one the module's manifest marks hideable;
    the list is kept in manifest order without repeats. The module's version
    moves when the list changes (ADR-180 point 2), and a stale one is refused.
    Hiding never touches a value: the record, the override and `module_data`
    keep theirs.
    """
    module = get_module(db, module_id, brand_id=brand_id)
    if module is None:
        return None
    refuse_stale(db, module, expected_updated_at, "module")
    channel_key = db.get(VariantDB, module.variant_id).channel
    manifest = get_manifest(channel_key, module.module_type)
    hideable = hideable_fields(manifest) if manifest is not None else []
    refused = [f for f in dict.fromkeys(fields) if f not in hideable]
    if refused:
        raise NotHideable(refused, module.module_type)
    before = list(module.hidden_fields or [])
    after = [f for f in hideable if f in set(fields)]
    if after != before:
        module.hidden_fields = after
        db.commit()
        db.refresh(module)
    return to_module_instance(module), before


def delete_module(
    db: Session, module_id: int, *, brand_id: int, expected_updated_at: datetime | None = None
) -> list[dict] | None:
    """Remove a module from its variant. Positions of the remaining modules are
    left as-is — the (variant_id, position) uniqueness only requires no
    duplicates, not a contiguous sequence, and rendering orders by position, so
    a gap is harmless. Any content overrides on the module go with it (they're
    meaningless once the module is gone).

    **Returns the overrides it erased** — possibly none — so the route can name
    them in the audit log, which is where their history survives (task-252,
    design pass D2). None means the module was not found; test with `is None`,
    because an empty list is falsy.
    """
    module = get_module(db, module_id, brand_id=brand_id)
    if module is None:
        return None
    refuse_stale(db, module, expected_updated_at, "module")

    from app.overrides.db_models import ContentOverrideDB

    overrides = db.query(ContentOverrideDB).filter(
        ContentOverrideDB.module_instance_id == module_id
    )
    removed = [
        {"id": o.id, "field_overrides": o.field_overrides, "active": o.active,
         "overridden_by": o.overridden_by}
        for o in overrides.all()
    ]
    overrides.delete()
    db.delete(module)
    db.commit()
    return removed


def move_module(
    db: Session, module_id: int, direction: str, *, brand_id: int,
    expected_updated_at: datetime | None = None,
) -> ModuleInstance | None:
    """Move a module one step up or down within its variant by swapping its
    position with the adjacent module. No-op if already at the top/bottom.

    The token is the moved module's own: the neighbour it swaps with moves as
    a consequence, and the caller never read the neighbour's version to state
    it."""
    if direction not in ("up", "down"):
        raise ValueError("direction must be 'up' or 'down'")

    module = get_module(db, module_id, brand_id=brand_id)
    if module is None:
        return None
    refuse_stale(db, module, expected_updated_at, "module")

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
    expected_updated_at: datetime | None = None,
) -> DecisionSlotDB | None:
    slot = get_decision_slot(db, slot_id, brand_id=brand_id)
    if slot is None:
        return None
    refuse_stale(db, slot, expected_updated_at, "decision slot")
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


def attach_new_slot(
    db: Session,
    module_id: int,
    decision_strategy: str = "top_score",
    *,
    brand_id: int,
    expected_updated_at: datetime | None = None,
):
    """Fill a catalogue module from a new decision slot, in one transaction
    (task-264). Returns `(module, slot)`, or None when the module is not in
    this brand.

    Variant Editor interview 1.3: a slot is configured on its module, in
    place. Creating the slot and binding the module were two writes, and a
    failure between them left a slot nothing used. The module's version is
    checked first (ADR-180 point 2). Only a catalogue module takes a slot: a
    static module's fields are typed in, and nothing would read a pick. Any
    override on the module stays in its table but stops applying, because
    a slot is never overridden (ADR-186 point 5).
    """
    module = get_module(db, module_id, brand_id=brand_id)
    if module is None:
        return None
    refuse_stale(db, module, expected_updated_at, "module")
    variant = db.get(VariantDB, module.variant_id)
    manifest = get_manifest(variant.channel, module.module_type)
    if manifest is None or not manifest.cms:
        raise ValueError(
            f"'{module.module_type}' takes its fields from the module itself, so a "
            "decision slot would have nothing to fill. Only a catalogue module takes one."
        )
    candidate_filter, strategy_config = _normalize_for_strategy(decision_strategy, None, None)
    slot = DecisionSlotDB(
        variant_id=module.variant_id,
        name=f"{manifest.label} (position {module.position})",
        decision_type="content_recommendation",
        decision_strategy=decision_strategy,
        candidate_filter=candidate_filter,
        strategy_config=strategy_config,
        max_results=1,
    )
    db.add(slot)
    db.flush()
    module.content_record_id = None
    module.decision_slot_id = slot.id
    db.commit()
    db.refresh(module)
    db.refresh(slot)
    return to_module_instance(module), slot


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


def page_resolutions_for_decision_slot(db: Session, decision_slot_id: int, params, *, brand_id: int):
    """One ADR-185 page of a slot's resolutions, newest first — the worst
    unbounded read the Manager Workflow interview named (Cluster 3 gap 10)."""
    from app.pagination import page_of_query

    query = (
        db.query(DecisionResolutionDB)
        .join(DecisionSlotDB, DecisionSlotDB.id == DecisionResolutionDB.decision_slot_id)
        .join(VariantDB, VariantDB.id == DecisionSlotDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(DecisionResolutionDB.decision_slot_id == decision_slot_id,
                CampaignDB.brand_id == brand_id)
    )
    return page_of_query(query, params, DecisionResolutionDB.created_at.desc(),
                         DecisionResolutionDB.id.desc(), convert=to_decision_resolution)


def page_decision_slots_with_stats(db: Session, params, *, brand_id: int):
    """One ADR-185 page of the brand's slots with their counts. Ordered by
    campaign, variant, slot — the order a person reads a campaign in."""
    from app.pagination import page_of_list

    # Grouped and aggregated in one query already; paging the assembled rows
    # keeps that one query instead of a second count over a GROUP BY.
    return page_of_list(list_decision_slots_with_stats(db, brand_id=brand_id), params)




# --- decision-slot read models (task-50, B21/B22) ------------------------------
# Lifted from the Jinja decisions pages, which computed them in the router: the
# SPA must not rebuild aggregates, and the composition read needs them too.

def list_decision_slots_with_stats(db: Session, *, brand_id: int) -> list[dict]:
    """Every decision slot in the brand, with its campaign and variant and three
    aggregates: resolutions, distinct content picked, and the latest pick."""
    rows = (
        db.query(
            DecisionSlotDB, VariantDB.id, VariantDB.name, CampaignDB.id, CampaignDB.name,
            func.count(DecisionResolutionDB.id),
            func.count(func.distinct(DecisionResolutionDB.content_record_id)),
            func.max(DecisionResolutionDB.created_at),
        )
        .join(VariantDB, DecisionSlotDB.variant_id == VariantDB.id)
        .join(CampaignDB, VariantDB.campaign_id == CampaignDB.id)
        .filter(CampaignDB.brand_id == brand_id)
        .outerjoin(DecisionResolutionDB, DecisionResolutionDB.decision_slot_id == DecisionSlotDB.id)
        .group_by(DecisionSlotDB.id, VariantDB.id, VariantDB.name, CampaignDB.id, CampaignDB.name)
        .order_by(CampaignDB.id.asc(), VariantDB.id.asc(), DecisionSlotDB.id.asc())
        .all()
    )
    return [
        {
            "id": slot.id, "name": slot.name, "decision_type": slot.decision_type,
            "decision_strategy": slot.decision_strategy,
            "variant_id": variant_id, "variant_name": variant_name,
            "campaign_id": campaign_id, "campaign_name": campaign_name,
            "resolution_count": count, "unique_content_count": unique, "last_resolution_at": last,
            "updated_at": slot.updated_at,
        }
        for slot, variant_id, variant_name, campaign_id, campaign_name, count, unique, last in rows
    ]


def decision_slot_stats(db: Session, slot_id: int, *, brand_id: int) -> dict | None:
    """One slot in the brand, with what it has picked: a summary, the top 20
    content with their share, the latest 50 picks and a reason histogram.
    None when the slot is not in this brand."""
    context = (
        db.query(DecisionSlotDB, VariantDB.id, VariantDB.name, CampaignDB.id, CampaignDB.name)
        .join(VariantDB, DecisionSlotDB.variant_id == VariantDB.id)
        .join(CampaignDB, VariantDB.campaign_id == CampaignDB.id)
        .filter(DecisionSlotDB.id == slot_id, CampaignDB.brand_id == brand_id)
        .first()
    )
    if context is None:
        return None
    slot, variant_id, variant_name, campaign_id, campaign_name = context
    of_slot = DecisionResolutionDB.decision_slot_id == slot_id

    s = db.query(
        func.count(DecisionResolutionDB.id),
        func.count(func.distinct(DecisionResolutionDB.recipient_id)),
        func.count(func.distinct(DecisionResolutionDB.content_record_id)),
        func.coalesce(func.avg(DecisionResolutionDB.score), 0),
        func.coalesce(func.min(DecisionResolutionDB.score), 0),
        func.coalesce(func.max(DecisionResolutionDB.score), 0),
        func.max(DecisionResolutionDB.created_at),
    ).filter(of_slot).first()
    total = s[0] or 0
    top = (
        db.query(ContentRecordDB.id, ContentRecordDB.title, ContentVersionDB.version_number,
                 func.count(DecisionResolutionDB.id).label("selection_count"))
        .join(ContentRecordDB, DecisionResolutionDB.content_record_id == ContentRecordDB.id)
        .outerjoin(ContentVersionDB, DecisionResolutionDB.content_version_id == ContentVersionDB.id)
        .filter(of_slot)
        .group_by(ContentRecordDB.id, ContentRecordDB.title, ContentVersionDB.version_number)
        .order_by(desc("selection_count")).limit(20).all()
    )
    latest = (
        db.query(DecisionResolutionDB, ContentRecordDB.title, ContentVersionDB.version_number)
        .join(ContentRecordDB, DecisionResolutionDB.content_record_id == ContentRecordDB.id)
        .outerjoin(ContentVersionDB, DecisionResolutionDB.content_version_id == ContentVersionDB.id)
        .filter(of_slot).order_by(DecisionResolutionDB.created_at.desc()).limit(50).all()
    )
    reasons = (
        db.query(DecisionResolutionDB.reason, func.count(DecisionResolutionDB.id).label("count"))
        .filter(of_slot).group_by(DecisionResolutionDB.reason)
        .order_by(desc("count")).limit(20).all()
    )
    return {
        "slot": slot,
        "variant_id": variant_id, "variant_name": variant_name,
        "campaign_id": campaign_id, "campaign_name": campaign_name,
        "summary": {
            "resolution_count": total, "unique_recipient_count": s[1], "unique_content_count": s[2],
            "avg_score": round(float(s[3]), 2), "min_score": round(float(s[4]), 2),
            "max_score": round(float(s[5]), 2), "last_resolution_at": s[6],
        },
        "top_content": [
            {"content_id": cid, "title": title, "version_number": version, "selection_count": n,
             "share": round(n / total * 100, 2) if total else 0}
            for cid, title, version, n in top
        ],
        "latest": [
            {"id": r.id, "recipient_id": r.recipient_id, "content_record_id": r.content_record_id,
             "content_title": title, "content_version": version, "score": r.score,
             "reason": r.reason, "created_at": r.created_at}
            for r, title, version in latest
        ],
        "reasons": [{"reason": reason, "count": count} for reason, count in reasons],
    }



def slot_candidate_count(db: Session, slot_id: int, *, brand_id: int) -> dict | None:
    """How many content records one slot would choose between, without
    resolving it (task-205). `POST /decision/slots/{id}/execute` writes a
    resolution, so it cannot answer this; this reads only.

    None when the slot is not in this brand. Raises `BrokenCampaignChain` as
    execution does, and `ValueError` for a strategy the registry does not know.
    """
    from app.decision.strategies.registry import get_strategy
    from app.decision.strategies.base import candidate_query, sending_brand_id

    slot = get_decision_slot(db, slot_id, brand_id=brand_id)
    if slot is None:
        return None
    meta = get_strategy(slot.decision_strategy).meta
    count = (
        candidate_query(db, slot, brand_id=sending_brand_id(db, slot))
        .with_entities(func.count(func.distinct(ContentRecordDB.id)))
        .scalar()
    )
    return {
        "slot_id": slot.id,
        "candidate_count": count or 0,
        "category_ids": (slot.candidate_filter or {}).get("category_ids", []),
        "requires_recipient": meta.requires_recipient,
    }


def campaign_composition(db: Session, campaign_id: int, *, brand_id: int) -> dict | None:
    """A campaign as the variant editor shows it (task-50, B11). None when the
    campaign is not in this brand.

    Per variant: its modules in order — each with whether it may be overridden
    (`overrides.service.is_overrideable`) and its active override — with the
    envelope module (subject, preheader) reported apart, the channel's module
    limit and whether another fits, the module types the channel accepts, and
    each decision slot with its counts. Everything a client would otherwise
    rebuild from manifests and channel rules; snapshots, audiences and
    providers have their own reads.
    """
    from app.channels.registry import max_modules_for
    from app.modules.registry import envelope_module_type, get_manifest, list_manifests
    from app.overrides.service import get_active_content_override, is_overrideable
    from app.campaigns.fence import view as fence_view

    campaign = get_campaign(db, campaign_id, brand_id=brand_id)
    if campaign is None:
        return None
    slot_stats = {row["id"]: row for row in list_decision_slots_with_stats(db, brand_id=brand_id)
                  if row["campaign_id"] == campaign_id}
    # Names, not ids: "Record #65" tells a manager nothing (2026-10-04). One
    # query for every record the campaign's modules are bound to, kept within
    # the brand, so a binding that somehow crossed it names nothing.
    record_titles = dict(
        db.query(ContentRecordDB.id, ContentRecordDB.title)
        .join(ModuleInstanceDB, ModuleInstanceDB.content_record_id == ContentRecordDB.id)
        .join(VariantDB, VariantDB.id == ModuleInstanceDB.variant_id)
        .filter(VariantDB.campaign_id == campaign_id, ContentRecordDB.brand_id == brand_id)
        .all()
    )
    variants = []
    for variant in (db.query(VariantDB).filter(VariantDB.campaign_id == campaign_id)
                    .order_by(VariantDB.id.asc()).all()):
        modules, envelope_modules = [], []
        for m in (db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id)
                  .order_by(ModuleInstanceDB.position.asc()).all()):
            manifest = get_manifest(variant.channel, m.module_type)
            overrideable = is_overrideable(manifest, m)
            active = get_active_content_override(db, m.id) if overrideable else None
            row = {
                "id": m.id, "position": m.position, "module_type": m.module_type,
                "content_record_id": m.content_record_id, "decision_slot_id": m.decision_slot_id,
                "content_record_title": record_titles.get(m.content_record_id),
                "decision_slot_name": (slot_stats.get(m.decision_slot_id) or {}).get("name"),
                "module_data": m.module_data or {},
                "hidden_fields": list(m.hidden_fields or []),
                "known": manifest is not None, "updated_at": m.updated_at,
                "overrideable": overrideable,
                "active_override": (
                    {"id": active.id, "field_overrides": active.field_overrides or {},
                     "overridden_by": active.overridden_by, "reason": active.reason}
                    if active is not None else None
                ),
            }
            is_envelope = bool(manifest and any(v.envelope for v in manifest.variables))
            (envelope_modules if is_envelope else modules).append(row)
        limit = max_modules_for(variant.channel)
        variants.append({
            "variant": to_variant(variant, db), "fence": fence_view(variant),
            "module_limit": limit,
            "can_add_module": limit is None or len(modules) < limit,
            "has_envelope": envelope_module_type(variant.channel) is not None,
            "accepted_module_types": [
                m.name for m in list_manifests(variant.channel)
                if not any(v.envelope for v in m.variables)
            ],
            "modules": modules,
            "envelope_modules": envelope_modules,
            "decision_slots": [
                slot_stats[slot.id] for slot in
                db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == variant.id)
                .order_by(DecisionSlotDB.id.asc()).all()
                if slot.id in slot_stats
            ],
        })
    return {"campaign": campaign, "variants": variants}
