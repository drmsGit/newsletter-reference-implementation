"""Duplicating a campaign — the escape hatch ADR-150 point 2 creates.

A content record belongs to exactly one brand, so a campaign cannot be shared
into a second one. Duplication is what replaces that. The user's original
premise was *"Duplication is a risky topic, so why do it with a one-click
solution. Make the manager make his decision deliberately instead of fast."*
Since the Variant Editor interview (Q5.1) that friction applies only where it
earns its place: duplicating within a campaign is one click, and the deliberate
wizard remains for copying into another brand, because forking content is the
risky case (friction follows risk, the 2026-07-05 rule; business baseline
P2-A3, 2026-10-09).

**The rule that decides everything is the boundary, not the act.** Duplicating a
campaign does not imply duplicating content; crossing a brand boundary does.

  - **Same brand** — the copy's modules reference the *same* content records.
    No content rows are created at all. This is ADR-013 working normally:
    compositions store references so catalogue edits reach live campaigns.
  - **Different brand** — content must be copied, because a record carries one
    `brand_id`. This is the carve-out ADR-013's 2026-09-16 addendum names, not
    the default.

Stated that way, copying content stops being a preference the manager expresses
and becomes a consequence of where they are sending the copy.

**Why this writes rows itself instead of calling the service layer.**
`create_campaign`, `create_variant_for_campaign` and `create_content` each
commit. Chained, a failure halfway through leaves a persisted campaign holding
some of its modules and none of its slots — a copy that *looks* finished and is
silently partial, which is the exact failure the whole deliberate-wizard design
exists to prevent. So this module opens one transaction, flushes for ids, and
commits once. The cost is that it re-states the rules those creators own; the
ones that matter here are `position` contiguity and the module check constraint,
both asserted in tests.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.auth.db_models import BrandDB
from app.auth.permissions import CAMPAIGNS_MANAGE, CONTENT_MANAGE, OVERRIDES_MANAGE
from app.auth.service import actor_label, has_permission, list_brands
from app.campaigns.db_models import (
    CampaignDB,
    DecisionSlotDB,
    ModuleInstanceDB,
    VariantDB,
)
from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
from app.modules.registry import envelope_module_type
from app.overrides.db_models import ContentOverrideDB

#: What happens to the content the source campaign's modules point at.
KEEP = "keep"      # same brand only — modules reference the same records
COPY = "copy"      # different brand only — records are duplicated across
LAYOUT = "layout"  # either — modules arrive unbound

_NAME_LIMIT = 255


class DuplicationRefused(ValueError):
    """The request cannot be honoured — wrong content mode for the boundary,
    or a source that does not exist. A ValueError subclass so the UI routes
    that already catch ValueError keep working."""


class DuplicationNotFound(DuplicationRefused):
    """The source, or the target campaign, is not in the working brand.

    One answer for "does not exist" and "exists in another brand", as
    ADR-172 point 6 requires, so the JSON plane can make both a 404.
    """


class DuplicationForbidden(DuplicationRefused):
    """The caller holds no grant that lets them write into the target brand.

    A subclass of `DuplicationRefused` so a caller that does not care which
    refusal it is keeps working; the JSON plane tells them apart because "you
    may not" is a 403 and "that cannot be done" is a 409.
    """


def require_target_access(
    db: Session,
    principal,
    *,
    target_brand_id: int,
    noun: str,
    permission: str,
    enforced: bool = True,
) -> BrandDB:
    """The target half of the duplication rule (task-50), enforced once.

    **Why this exists.** The policy table checks a permission against the
    *working* brand only, and duplication names a second one. Without this, a
    Manager on brand A creates a campaign in brand B by choosing B as the
    target — the check passes because it never looked at the destination. The
    rule lived in `frontend/router.py`, the Jinja UI the SPA is meant to
    replace (task-50), so retiring it would have retired the only enforcement.

    **One answer for a brand that does not exist and a brand the caller holds
    no grant on** — the difference would tell a signed-in caller which brands
    exist beyond their own, as `set_session_brand` refuses to.

    `enforced=False` is the auth-off posture (nobody signed in, so there are no
    grants to read): any existing brand is a legal target, matching what
    `working_brand_id` does on the Jinja plane.
    """
    brand = db.get(BrandDB, target_brand_id)
    if brand is None or (
        enforced and not has_permission(db, principal, permission, brand_id=brand.id)
    ):
        raise DuplicationForbidden(f"You cannot create {noun} in that brand.")
    return brand


def require_campaign_target(
    db: Session, principal, *, target_brand_id: int, content_mode: str,
    enforced: bool = True,
):
    """`campaigns.manage` on the target, and for COPY also `content.manage`
    there: copying creates content rows in the target brand, so the working
    brand's content permission says nothing about it."""
    brand = require_target_access(
        db, principal, target_brand_id=target_brand_id, noun="campaigns",
        permission=CAMPAIGNS_MANAGE, enforced=enforced,
    )
    if content_mode == COPY and enforced and not has_permission(
        db, principal, CONTENT_MANAGE, brand_id=brand.id
    ):
        raise DuplicationForbidden(
            "Copying content creates records in the target brand, and you cannot "
            "edit content there. Take the layout only."
        )
    return brand


def require_content_target(
    db: Session, principal, *, target_brand_id: int, enforced: bool = True,
):
    return require_target_access(
        db, principal, target_brand_id=target_brand_id, noun="content",
        permission=CONTENT_MANAGE, enforced=enforced,
    )


@dataclass
class DuplicationReport:
    """What the copy actually did, as facts. The wording is the template's job.

    This is also what gets written to the audit log, which is how ADR-153
    answers "where did this campaign come from?" without a `copied_from_id`
    column that could go stale — the same reason ADR-163 stores consent as
    events and computes the answer from them.
    """
    campaign_id: int
    source_campaign_id: int
    source_brand_id: int
    target_brand_id: int
    content_mode: str
    variants: int = 0
    modules: int = 0
    decision_slots: int = 0
    #: source content record id -> the new record's id. Empty unless COPY.
    content_records_copied: dict[int, int] = field(default_factory=dict)
    #: Places a brand-specific URL came across verbatim, as readable labels.
    url_carriers: list[str] = field(default_factory=list)
    #: Active overrides reproduced on the copy, and ones LAYOUT had to drop
    #: because their module arrived unbound (task-113).
    overrides_carried: int = 0
    overrides_not_carried: int = 0

    @property
    def crossed_brands(self) -> bool:
        return self.target_brand_id != self.source_brand_id

    def as_detail(self) -> dict:
        """The audit entry's payload.

        Note `content_records_copied` survives the round trip through the JSON
        column with **string keys** — JSON object keys are strings, so a later
        "which record produced this copy?" query has to look for `str(id)`.
        Said here rather than discovered by whoever writes that query.
        """
        return {
            "source_campaign_id": self.source_campaign_id,
            "source_brand_id": self.source_brand_id,
            "target_brand_id": self.target_brand_id,
            "content_mode": self.content_mode,
            "variants": self.variants,
            "modules": self.modules,
            "decision_slots": self.decision_slots,
            "content_records_copied": self.content_records_copied,
            "overrides_carried": self.overrides_carried,
            "overrides_not_carried": self.overrides_not_carried,
        }


@dataclass
class VariantDuplicationReport:
    """What a variant copy did (task-229) — the audit entry's payload, like
    `DuplicationReport`, and for the same ADR-153 reason: provenance is an
    event, not a `copied_from_id` column that could go stale."""
    variant_id: int
    source_variant_id: int
    campaign_id: int
    source_campaign_id: int
    content_mode: str
    variants: int = 0
    modules: int = 0
    decision_slots: int = 0
    #: Always empty — a variant copy never leaves its brand — but the shared
    #: copy helper tallies into it.
    content_records_copied: dict[int, int] = field(default_factory=dict)
    url_carriers: list[str] = field(default_factory=list)
    overrides_carried: int = 0
    overrides_not_carried: int = 0

    def as_detail(self) -> dict:
        return {
            "overrides_carried": self.overrides_carried,
            "overrides_not_carried": self.overrides_not_carried,
            "source_variant_id": self.source_variant_id,
            "source_campaign_id": self.source_campaign_id,
            "campaign_id": self.campaign_id,
            "content_mode": self.content_mode,
            "modules": self.modules,
            "decision_slots": self.decision_slots,
        }


def content_modes_for(source_brand_id: int, target_brand_id: int) -> list[str]:
    """The modes that are expressible for this pair, in UI order.

    Not a preference list — the excluded one in each case cannot be built.
    Referencing across brands would put a record in two brands; copying inside
    one brand would fork the catalogue for no reason the schema requires.
    """
    if source_brand_id == target_brand_id:
        return [KEEP, LAYOUT]
    return [COPY, LAYOUT]


def target_brands(
    db: Session, principal, *, permission: str, enforced: bool = True,
) -> list[BrandDB]:
    """Brands this caller may duplicate *into*, ordered by id (task-50, B14).

    The listing twin of `require_target_access`, and the same rule: it asks the
    caller's own grants on each brand, so a person and an integration alike see
    exactly the brands a duplication request would be accepted for. Not
    `brands_for_user` — see `require_target_access` for why the working brand's
    permission says nothing about a destination.
    """
    brands = list_brands(db)
    if not enforced:
        return brands
    return [b for b in brands if has_permission(db, principal, permission, brand_id=b.id)]


def allowed_modes(
    db: Session, principal, *, source_brand_id: int, target_brand_id: int,
    enforced: bool = True,
) -> list[str]:
    """The content modes this caller may use for this pair: what the boundary
    allows (`content_modes_for`) minus `copy` unless they hold `content.manage`
    on the target, since copying writes content rows there."""
    modes = content_modes_for(source_brand_id, target_brand_id)
    if enforced and not has_permission(db, principal, CONTENT_MANAGE, brand_id=target_brand_id):
        modes = [m for m in modes if m != COPY]
    return modes


def _url_keys(data: dict | None) -> list[str]:
    if not isinstance(data, dict):
        return []
    return [k for k in data if k == "url" or k.endswith("_url")]


def _clamp(name: str) -> str:
    return (name or "").strip()[:_NAME_LIMIT]


def duplicate_campaign(
    db: Session,
    *,
    campaign_id: int,
    target_brand_id: int,
    name: str,
    content_mode: str,
    variant_ids: list[int] | None = None,
    principal,
    enforced: bool,
) -> DuplicationReport:
    """Copy one campaign into `target_brand_id`, which may be its own brand.

    Copied: the campaign, its variants, their modules (with `module_data` as-is)
    and their decision slots — the slots as *prepared spots*, carrying their
    name, type, strategy and `max_results` but **no `candidate_filter` or
    `strategy_config`**. A configured slot that resolves nothing looks finished;
    an empty one is visibly incomplete, and the manager should choose against
    the content that now exists rather than inherit a filter chosen against
    content that may not.

    Not copied: resolutions, snapshots, send instances, delivery executions
    and content versions. Each of those is a record of something that
    *happened*, and a copy has no history — reproducing them would fabricate
    decisions, publications and sends.

    **Active content overrides do come across** (task-113), because an
    override is two things in one row: a record of a manager's act *and* live
    configuration that every render reads. Dropping it made the copy render
    differently from its original with nothing said. So the line is drawn
    inside the row — see `_carry_override`.

    Status is forced to draft throughout, for the same reason: a copy of a sent
    campaign has not been sent.

    **`variant_ids` selects which variants come across**; None means all, which
    keeps "duplicate this campaign" the default. It earned its place when
    variants gained channels (ADR-160 point 4): "duplicate this campaign" then
    started meaning "duplicate its email *and* its push", and giving another
    brand only the push had no expression short of deleting the rest
    afterwards. An empty selection is refused rather than silently treated as
    all — a campaign must always have a variant, and a request that names none
    is a mistake rather than a shorthand.
    """
    source = db.query(CampaignDB).filter(CampaignDB.id == campaign_id).first()
    if source is None:
        raise DuplicationRefused("That campaign does not exist.")

    allowed = content_modes_for(source.brand_id, target_brand_id)
    if content_mode not in allowed:
        if content_mode == KEEP:
            raise DuplicationRefused(
                "Content cannot be referenced across brands — a content record "
                "belongs to exactly one brand (ADR-150 point 2). Copy it or "
                "take the layout only."
            )
        if content_mode == COPY:
            raise DuplicationRefused(
                "Content is not copied inside a brand — the copy references the "
                "same records, so catalogue edits still reach it (ADR-013)."
            )
        raise DuplicationRefused(f"Unknown content option: {content_mode!r}")

    clean_name = _clamp(name) or f"{source.name} (copy)"[:_NAME_LIMIT]

    report = DuplicationReport(
        campaign_id=0,
        source_campaign_id=source.id,
        source_brand_id=source.brand_id,
        target_brand_id=target_brand_id,
        content_mode=content_mode,
    )

    query = db.query(VariantDB).filter(VariantDB.campaign_id == source.id)
    if variant_ids is not None:
        if not variant_ids:
            raise DuplicationRefused(
                "Choose at least one variant — a campaign cannot exist without one."
            )
        query = query.filter(VariantDB.id.in_(variant_ids))
    variants = query.order_by(VariantDB.id.asc()).all()

    if not variants:
        raise DuplicationRefused(
            "None of the chosen variants belong to this campaign."
        )

    # Before anything is written, so a refusal leaves nothing behind.
    _require_override_grant(
        db, principal, brand_id=target_brand_id, content_mode=content_mode,
        variant_ids=[v.id for v in variants], enforced=enforced,
    )
    actor = actor_label(principal)

    campaign = CampaignDB(name=clean_name, status="draft", brand_id=target_brand_id)
    db.add(campaign)
    db.flush()

    for source_variant in variants:
        _copy_variant_into(
            db, source_variant, campaign_id=campaign.id, name=source_variant.name,
            content_mode=content_mode, target_brand_id=target_brand_id, report=report,
            actor=actor,
        )

    db.commit()
    db.refresh(campaign)
    report.campaign_id = campaign.id
    return report


def default_variant_mode(source_campaign_id: int, target_campaign_id: int) -> str:
    """The content mode a variant copy takes when none is named (task-229).

    **It depends on where the copy goes**, decided 2026-10-02 from the Variant
    Editor interview's own observation (Q5.2):

      - **Into its own campaign: KEEP.** That is an A/B/C arm, or a variant
        carrying a record meant for one audience group. It wants everything
        identical except the thing under test, and LAYOUT would make the manager
        rebind every module, which defeats the point.
      - **Into another campaign: LAYOUT.** That is the weekly newsletter.
        `module_data` and the envelope come across in every mode, so the
        furniture survives and last week's news does not.

    A mode the caller names always wins. This only fills the gap.
    """
    return KEEP if target_campaign_id == source_campaign_id else LAYOUT


def duplicate_variant(
    db: Session,
    *,
    variant_id: int,
    brand_id: int,
    target_campaign_id: int | None = None,
    name: str | None = None,
    content_mode: str | None = None,
    principal,
    enforced: bool,
) -> VariantDuplicationReport:
    """Copy one variant into a campaign of the same brand — by default its own.

    **The primary way a variant comes into being** (Variant Editor interview
    Q5.1), and deliberately narrower than `duplicate_campaign` (Q5.6): **same
    brand only**, so it never needs COPY, never carries a URL across a brand
    and never forks the catalogue. The cross-brand story stays a campaign-level
    act, where a manager is already thinking about brands.

    It inherits everything else by sharing `_copy_variant_into`: slots arrive as
    prepared spots, positions are renumbered with the envelope at 0, the channel
    is carried (ADR-160 point 5), status is draft, and nothing that *happened*
    comes across. One commit, for the reason the module docstring gives.

    Active content overrides come across too, by the same rule and the same
    permission (task-113): see `_carry_override` and `_require_override_grant`.
    """
    from app.campaigns.service import brand_of_variant

    source = db.get(VariantDB, variant_id)
    if source is None or brand_of_variant(db, variant_id) != brand_id:
        raise DuplicationNotFound("That variant does not exist.")

    campaign_id = target_campaign_id if target_campaign_id is not None else source.campaign_id
    target = (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id, CampaignDB.brand_id == brand_id)
        .first()
    )
    if target is None:
        raise DuplicationNotFound("That campaign does not exist.")

    mode = content_mode or default_variant_mode(source.campaign_id, target.id)
    if mode not in content_modes_for(brand_id, brand_id):
        if mode == COPY:
            raise DuplicationRefused(
                "Content is not copied inside a brand — the copy references the "
                "same records, so catalogue edits still reach it (ADR-013)."
            )
        raise DuplicationRefused(f"Unknown content option: {mode!r}")

    _require_override_grant(
        db, principal, brand_id=brand_id, content_mode=mode,
        variant_ids=[source.id], enforced=enforced,
    )

    report = VariantDuplicationReport(
        variant_id=0,
        source_variant_id=source.id,
        campaign_id=target.id,
        source_campaign_id=source.campaign_id,
        content_mode=mode,
    )
    variant = _copy_variant_into(
        db, source, campaign_id=target.id,
        name=_clamp(name or "") or f"{source.name} (copy)"[:_NAME_LIMIT],
        content_mode=mode, target_brand_id=brand_id, report=report,
        actor=actor_label(principal),
    )
    db.commit()
    report.variant_id = variant.id
    return report


def _copy_variant_into(
    db: Session,
    source_variant: VariantDB,
    *,
    campaign_id: int,
    name: str,
    content_mode: str,
    target_brand_id: int,
    report,
    actor: str,
) -> VariantDB:
    """One variant, its decision slots and its modules, into `campaign_id`,
    inside the caller's transaction (flushed, never committed).

    **The one place a variant is copied**, for a whole campaign and for a single
    variant alike. Variant Editor interview Q5.6 settled that variant
    duplication reuses this machinery rather than reimplementing a subset,
    because a parallel copy starts as a subset and drifts — the argument
    ADR-160 point 6 makes about registration patterns.

    `report` is tallied in place (`variants`, `modules`, `decision_slots`,
    `url_carriers`, `content_records_copied`), whichever report it is.
    """
    variant = VariantDB(
        campaign_id=campaign_id,
        # Carried, never re-chosen. ADR-160 point 5 fixes a variant's
        # channel at creation because switching it would invalidate the
        # modules, the content-readiness and the renderer at once — and a
        # copy whose modules came from a push variant is a push variant.
        channel=source_variant.channel,
        name=name,
        # Envelope copy is NOT carried here any more: it lives in the
        # header module (ADR-162 point 1), which the module loop below
        # copies like any other. Copying the columns too would restore the
        # second source of truth that point exists to remove.
        status="draft",
    )
    db.add(variant)
    db.flush()
    report.variants += 1

    slot_map: dict[int, int] = {}
    source_slots = (
        db.query(DecisionSlotDB)
        .filter(DecisionSlotDB.variant_id == source_variant.id)
        .order_by(DecisionSlotDB.id.asc())
        .all()
    )
    for source_slot in source_slots:
        slot = DecisionSlotDB(
            variant_id=variant.id,
            name=source_slot.name,
            decision_type=source_slot.decision_type,
            decision_strategy=source_slot.decision_strategy,
            candidate_filter=None,
            strategy_config=None,
            max_results=source_slot.max_results,
        )
        db.add(slot)
        db.flush()
        slot_map[source_slot.id] = slot.id
        report.decision_slots += 1

    source_modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == source_variant.id)
        .order_by(ModuleInstanceDB.position.asc())
        .all()
    )
    # Positions are re-numbered from 1 rather than carried over: deleting a
    # module leaves a hole, and a copy is a fresh composition with no reason
    # to inherit one. Iterating in source order keeps the layout identical.
    #
    # **The envelope module keeps position 0**, which is where
    # `set_envelope_fields` puts it on a fresh variant (ADR-162 point 1).
    # Letting it renumber to 1 would work — the renderer only cares that it
    # is first — but it would leave originals and copies structured
    # differently for no reason, and "first" is easier to rely on when it is
    # always the same number.
    envelope_type = envelope_module_type(variant.channel)
    next_position = 0
    for source_module in source_modules:
        if source_module.module_type == envelope_type:
            index = 0
        else:
            next_position += 1
            index = next_position
        content_record_id = _target_content_id(
            db,
            source_module.content_record_id,
            content_mode=content_mode,
            target_brand_id=target_brand_id,
            report=report,
        )
        module = ModuleInstanceDB(
            variant_id=variant.id,
            module_type=source_module.module_type,
            position=index,
            content_record_id=content_record_id,
            # A decision slot is layout, not content: it arrives in every
            # mode, including layout-only, because what "layout only" drops
            # is the binding to a specific record.
            decision_slot_id=slot_map.get(source_module.decision_slot_id),
            module_data=source_module.module_data,
            # A layout choice, so it copies with the layout (ADR-187).
            hidden_fields=list(source_module.hidden_fields or []),
        )
        db.add(module)
        db.flush()
        report.modules += 1
        _carry_override(db, source_module, module, content_mode=content_mode,
                        actor=actor, report=report)
        for key in _url_keys(source_module.module_data):
            report.url_carriers.append(
                f"{source_variant.name} → module {index} ({source_module.module_type}): {key}"
            )
    return variant


def _carried_override_count(db: Session, variant_ids: list[int]) -> int:
    """Active overrides on these variants that a copy would reproduce: on
    modules bound to a record and not to a slot (ADR-178 point 5)."""
    if not variant_ids:
        return 0
    return (
        db.query(ContentOverrideDB)
        .join(ModuleInstanceDB, ModuleInstanceDB.id == ContentOverrideDB.module_instance_id)
        .filter(
            ModuleInstanceDB.variant_id.in_(variant_ids),
            ModuleInstanceDB.content_record_id.isnot(None),
            ModuleInstanceDB.decision_slot_id.is_(None),
            ContentOverrideDB.active.is_(True),
        )
        .count()
    )


def _require_override_grant(
    db: Session, principal, *, brand_id: int, content_mode: str,
    variant_ids: list[int], enforced: bool,
) -> None:
    """Carrying an override writes override rows in the target brand, so it
    needs `overrides.manage` there (task-113, decided 2026-10-02).

    The same shape as COPY needing `content.manage` on the target
    (`require_campaign_target`): ADR-150 keeps overriding apart from
    restructuring a campaign, and without this a person who may only
    restructure would create overrides by duplicating. LAYOUT carries none, so
    it needs nothing — which is what the refusal offers.
    """
    if not enforced or content_mode == LAYOUT:
        return
    count = _carried_override_count(db, variant_ids)
    if count and not has_permission(db, principal, OVERRIDES_MANAGE, brand_id=brand_id):
        plural = "s" if count != 1 else ""
        raise DuplicationForbidden(
            f"This copy would carry {count} active override{plural}, and you "
            "cannot manage overrides in that brand. Take the layout only, or ask "
            "someone who can."
        )


def _carry_override(
    db: Session, source_module: ModuleInstanceDB, module: ModuleInstanceDB, *,
    content_mode: str, actor: str, report,
) -> None:
    """Reproduce the source module's **active** override on its copy (task-113).

    **The line is drawn inside the row.** Carried: the edit
    (`field_overrides`), what it was applied to (`system_content_record_id`)
    and why (`reason`) — the live half, which the renderer reads. Not
    carried: `outcome_delta` and `send_instance_id`, which measure a send that
    happened, and `reverted_at`. A reset row is pure history and is never
    reproduced, which is the fabrication the campaign docstring warns about.

    Under LAYOUT the copy's module is unbound, so an override has nothing to
    attach to (an override needs a record, ADR-178 point 5). It is dropped and
    counted, so the report says so rather than the copy quietly differing.
    """
    source = (
        db.query(ContentOverrideDB)
        .filter(ContentOverrideDB.module_instance_id == source_module.id,
                ContentOverrideDB.active.is_(True))
        .first()
    )
    if source is None:
        return
    if module.content_record_id is None or module.decision_slot_id is not None:
        report.overrides_not_carried += 1
        return

    applied_to = source.system_content_record_id
    if content_mode == COPY and applied_to is not None:
        # The record it was applied to now has a copy in the target brand;
        # pointing at the original would cite another brand's row.
        applied_to = report.content_records_copied.get(applied_to)
    db.add(ContentOverrideDB(
        module_instance_id=module.id,
        field_overrides=dict(source.field_overrides or {}),
        system_content_record_id=applied_to,
        reason=source.reason,
        overridden_by=actor,
        active=True,
    ))
    report.overrides_carried += 1


def _target_content_id(
    db: Session,
    source_content_id: int | None,
    *,
    content_mode: str,
    target_brand_id: int,
    report: DuplicationReport,
) -> int | None:
    """Where a module's content binding points after the copy.

    The one line that differs between the two paths, which is why it is one
    function and not three branches spread through the loop.
    """
    if source_content_id is None or content_mode == LAYOUT:
        return None
    if content_mode == KEEP:
        return source_content_id

    existing = report.content_records_copied.get(source_content_id)
    if existing is not None:
        # Two modules citing one record must land on one copy, not two — the
        # catalogue would otherwise gain a duplicate per reference.
        return existing

    copy = _copy_content_row(db, source_content_id, target_brand_id)
    if copy is None:
        return None
    report.content_records_copied[source_content_id] = copy.id
    for key in _url_keys(copy.content):
        report.url_carriers.append(f"content “{copy.title}”: {key}")
    return copy.id


def _copy_content_row(
    db: Session, content_id: int, target_brand_id: int, title: str | None = None
) -> ContentRecordDB | None:
    """One content record into another brand, categories included, inside the
    caller's transaction. **Deliberately no `content_versions`** — ADR-128
    makes a version the audit answer to "what exactly did this recipient
    receive?", so copying one would fabricate a publication that never
    happened. The visible consequence is stated in the UI rather than hidden:
    the copy previews and cannot be sent until someone publishes it.

    `status` comes across unchanged. An archived record copied as active would
    quietly resurrect it, which is a decision the manager did not make.
    """
    source = db.query(ContentRecordDB).filter(ContentRecordDB.id == content_id).first()
    if source is None:
        return None

    copy = ContentRecordDB(
        brand_id=target_brand_id,
        title=_clamp(title or source.title),
        description=source.description,
        content=dict(source.content or {}),
        status=source.status,
    )
    db.add(copy)
    db.flush()

    # Categories are global (ADR-150 point 2's taxonomy line), so the copy
    # points at the same category rows with the same scores.
    assignments = (
        db.query(ContentCategoryAssignmentDB)
        .filter(ContentCategoryAssignmentDB.content_id == source.id)
        .all()
    )
    for assignment in assignments:
        db.add(
            ContentCategoryAssignmentDB(
                content_id=copy.id,
                category_id=assignment.category_id,
                score=assignment.score,
            )
        )
    return copy


def duplicate_content_record(
    db: Session, *, content_id: int, target_brand_id: int
) -> ContentRecordDB:
    """One record, one step, from the catalogue. No wizard.

    **Deliberately no "already duplicated?" guard**, per the 2026-09-16 design
    pass: a manager who types the same record twice by hand is not stopped
    either, and nothing breaks when they do. A guard here would be
    disproportionate to a problem the product already tolerates from another
    direction. The campaign wizard is where duplication is risky, because it
    multiplies; one record does not.
    """
    source = db.query(ContentRecordDB).filter(ContentRecordDB.id == content_id).first()
    if source is None:
        raise DuplicationRefused("That content record does not exist.")

    # Inside one brand the copy needs a distinguishable title, since the two
    # would otherwise be indistinguishable in the catalogue list. Across
    # brands the title is unambiguous already — it is the only one there.
    title = source.title
    if target_brand_id == source.brand_id:
        title = _clamp(f"{source.title} (copy)")

    copy = _copy_content_row(db, content_id, target_brand_id, title=title)
    if copy is None:  # pragma: no cover — guarded above
        raise DuplicationRefused("That content record does not exist.")
    db.commit()
    db.refresh(copy)
    return copy


def summarise_source(
    db: Session, campaign_id: int, variant_ids: list[int] | None = None
) -> dict:
    """What the copy will consist of — the asset list step 1 shows.

    Step 1 exists to make the size of the act visible before it is taken. A
    campaign with four variants and eleven modules is a different decision from
    a campaign with one of each, and nothing else on the page says so.

    **Scoped to `variant_ids` when given**, because step 2 counts the content
    records this copy will duplicate. Summarising the whole campaign while
    copying two of its four variants would advertise records that never get
    copied — a warning that is wrong in the direction of sounding worse,
    which is still wrong.
    """
    query = db.query(VariantDB).filter(VariantDB.campaign_id == campaign_id)
    if variant_ids is not None:
        query = query.filter(VariantDB.id.in_(variant_ids))
    variants = query.order_by(VariantDB.id.asc()).all()
    rows = []
    content_ids: set[int] = set()
    for variant in variants:
        modules = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant.id)
            .order_by(ModuleInstanceDB.position.asc())
            .all()
        )
        slots = (
            db.query(DecisionSlotDB)
            .filter(DecisionSlotDB.variant_id == variant.id)
            .count()
        )
        content_ids.update(m.content_record_id for m in modules if m.content_record_id)
        rows.append({
            "id": variant.id,
            "name": variant.name,
            # Shown in the picker: since ADR-160 point 4 "the email one" and
            # "the push one" is how a manager tells two variants apart, more
            # reliably than by a name somebody typed.
            "channel": variant.channel,
            "modules": len(modules),
            "decision_slots": slots,
        })

    titles = []
    if content_ids:
        titles = [
            record.title
            for record in db.query(ContentRecordDB)
            .filter(ContentRecordDB.id.in_(content_ids))
            .order_by(ContentRecordDB.id.asc())
            .all()
        ]

    return {
        "variants": rows,
        "module_count": sum(row["modules"] for row in rows),
        "decision_slot_count": sum(row["decision_slots"] for row in rows),
        "content_titles": titles,
    }
