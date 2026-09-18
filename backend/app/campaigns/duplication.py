"""Duplicating a campaign — the escape hatch ADR-150 point 2 creates.

A content record belongs to exactly one brand, so a campaign cannot be shared
into a second one. Duplication is what replaces that, and the design premise is
the user's: *"Duplication is a risky topic, so why do it with a one-click
solution. Make the manager make his decision deliberately instead of fast."*

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

from app.campaigns.db_models import (
    CampaignDB,
    DecisionSlotDB,
    ModuleInstanceDB,
    VariantDB,
)
from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
from app.modules.registry import envelope_module_type

#: What happens to the content the source campaign's modules point at.
KEEP = "keep"      # same brand only — modules reference the same records
COPY = "copy"      # different brand only — records are duplicated across
LAYOUT = "layout"  # either — modules arrive unbound

_NAME_LIMIT = 255


class DuplicationRefused(ValueError):
    """The request cannot be honoured — wrong content mode for the boundary,
    or a source that does not exist. A ValueError subclass so the UI routes
    that already catch ValueError keep working."""


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
) -> DuplicationReport:
    """Copy one campaign into `target_brand_id`, which may be its own brand.

    Copied: the campaign, its variants, their modules (with `module_data` as-is)
    and their decision slots — the slots as *prepared spots*, carrying their
    name, type, strategy and `max_results` but **no `candidate_filter` or
    `strategy_config`**. A configured slot that resolves nothing looks finished;
    an empty one is visibly incomplete, and the manager should choose against
    the content that now exists rather than inherit a filter chosen against
    content that may not.

    Not copied: resolutions, snapshots, send instances, delivery executions,
    content versions and content overrides. Each of those is a record of
    something that *happened*, and a copy has no history — reproducing them
    would fabricate decisions, publications and sends.

    Status is forced to draft throughout, for the same reason: a copy of a sent
    campaign has not been sent.
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

    campaign = CampaignDB(name=clean_name, status="draft", brand_id=target_brand_id)
    db.add(campaign)
    db.flush()

    variants = (
        db.query(VariantDB)
        .filter(VariantDB.campaign_id == source.id)
        .order_by(VariantDB.id.asc())
        .all()
    )

    for source_variant in variants:
        variant = VariantDB(
            campaign_id=campaign.id,
            # Carried, never re-chosen. ADR-160 point 5 fixes a variant's
            # channel at creation because switching it would invalidate the
            # modules, the content-readiness and the renderer at once — and a
            # copy whose modules came from a push variant is a push variant.
            channel=source_variant.channel,
            name=source_variant.name,
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
            )
            db.add(module)
            report.modules += 1
            for key in _url_keys(source_module.module_data):
                report.url_carriers.append(
                    f"{source_variant.name} → module {index} ({source_module.module_type}): {key}"
                )

    db.commit()
    db.refresh(campaign)
    report.campaign_id = campaign.id
    return report


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


def summarise_source(db: Session, campaign_id: int) -> dict:
    """What the copy will consist of — the asset list step 1 shows.

    Step 1 exists to make the size of the act visible before it is taken. A
    campaign with four variants and eleven modules is a different decision from
    a campaign with one of each, and nothing else on the page says so.
    """
    variants = (
        db.query(VariantDB)
        .filter(VariantDB.campaign_id == campaign_id)
        .order_by(VariantDB.id.asc())
        .all()
    )
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
            "name": variant.name,
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
