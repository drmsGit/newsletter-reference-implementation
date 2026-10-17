from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB


@dataclass
class StrategyResult:
    content_record_id: int
    content_version_id: int | None
    score: float
    reason: str


@dataclass
class ConfigField:
    """One declared key a strategy expects in its candidate_filter or
    strategy_config. Mirrors the `variables` manifest email module templates
    declare — it lets the UI/API lock a decision slot's config *structure* to
    the chosen strategy (only values editable, not which keys exist)."""

    name: str
    type: str  # "int" | "number" | "str" | "list[int]"
    required: bool = False
    default: Any = None
    description: str = ""


@dataclass
class StrategyMeta:
    name: str
    label: str
    description: str
    requires_recipient: bool = False
    # Declared shapes for the two JSON config columns on a decision slot.
    # Empty list = "this strategy takes no keys here" (anything supplied is
    # rejected). Enforced by normalize_slot_config at slot create/update.
    candidate_filter_fields: list[ConfigField] = field(default_factory=list)
    config_fields: list[ConfigField] = field(default_factory=list)


def _check_type(section: str, spec: "ConfigField", value: Any) -> None:
    ok = True
    if spec.type == "int":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif spec.type == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif spec.type == "str":
        ok = isinstance(value, str)
    elif spec.type == "list[int]":
        ok = isinstance(value, list) and all(
            isinstance(v, int) and not isinstance(v, bool) for v in value
        )
    if not ok:
        raise ValueError(
            f"{section} key '{spec.name}' must be of type {spec.type}, got "
            f"{type(value).__name__}"
        )


def _normalize_section(
    section: str, fields: list["ConfigField"], incoming: dict | None
) -> dict | None:
    incoming = incoming or {}
    declared = {f.name: f for f in fields}

    unknown = set(incoming) - set(declared)
    if unknown:
        allowed = sorted(declared) or "(none — this strategy takes no keys here)"
        raise ValueError(
            f"{section} has key(s) not declared by this strategy: "
            f"{sorted(unknown)}. Allowed: {allowed}"
        )

    result: dict[str, Any] = {}
    for name, spec in declared.items():
        if name in incoming:
            _check_type(section, spec, incoming[name])
            result[name] = incoming[name]
        elif spec.required:
            raise ValueError(
                f"{section} is missing required key '{name}' for this strategy"
            )
        elif spec.default is not None:
            # copy so a shared default (e.g. a list) can't be mutated in place
            result[name] = list(spec.default) if isinstance(spec.default, list) else spec.default

    return result or None


def normalize_slot_config(
    meta: StrategyMeta,
    candidate_filter: dict | None,
    strategy_config: dict | None,
) -> tuple[dict | None, dict | None]:
    """Validate a decision slot's candidate_filter/strategy_config against the
    chosen strategy's declared shape and return normalized copies (unknown
    keys rejected, defaults filled, types checked). Raises ValueError on any
    violation so it surfaces as a clean 400/error banner rather than crashing
    later at resolution time."""
    return (
        _normalize_section("candidate_filter", meta.candidate_filter_fields, candidate_filter),
        _normalize_section("strategy_config", meta.config_fields, strategy_config),
    )


class DecisionStrategy(ABC):

    @property
    @abstractmethod
    def meta(self) -> StrategyMeta:
        pass

    @abstractmethod
    def rank(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
        *,
        limit: int = 1,
        exclude: frozenset[int] = frozenset(),
    ) -> list[StrategyResult]:
        """
        The slot's best candidates, best first: at most `limit`, each record
        once, none of `exclude` (records an earlier slot in the same email
        already shows; ADR-084 addendum 2026-10-11). Empty when nothing
        suitable exists. Never raise for a missing-content case — the caller
        handles graceful degradation (ADR-086).
        """
        pass

    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
    ) -> StrategyResult | None:
        """The single best pick: the first of the ranking, or None."""
        ranked = self.rank(db, slot, recipient_id, limit=1)
        return ranked[0] if ranked else None


def best_per_record(rows, key, exclude: frozenset[int], limit: int) -> list:
    """`rows` sorted best first by the caller; one per record (a record in
    two categories appears once per category in `candidate_query`, and only
    its best row counts), skipping `exclude`, at most `limit`. `key` gives a
    row's record id."""
    seen: set[int] = set()
    out = []
    for row in rows:
        record_id = key(row)
        if record_id in seen or record_id in exclude:
            continue
        seen.add(record_id)
        out.append(row)
        if len(out) == limit:
            break
    return out


class BrokenCampaignChain(RuntimeError):
    """A decision slot whose variant → campaign → brand chain does not resolve.

    **Deliberately not a ValueError** (task-18). The send loop catches
    ValueError from a slot as "the strategy resolved nothing" and hides the
    slot under ADR-086's graceful degradation — the right answer to an empty
    candidate set and the wrong one to a structural fault. And not a
    ConsentDenied either: that is what a broken chain used to surface as, via
    `require_consent(..., None)`, naming "brand None" — a compliance-shaped
    error for a data defect. This propagates, so a send fails loudly and the
    error says what is actually wrong.
    """


def sending_brand_id(db, slot) -> int:
    """The brand of the campaign this decision slot belongs to (ADR-150 point 8).

    A slot hangs off a variant, which hangs off a campaign, which carries the
    brand. **Raises `BrokenCampaignChain` if that chain does not resolve**
    (task-18), rather than returning None. It used to return None, and every
    caller stayed safe only by accident: `ContentRecordDB.brand_id == None`
    renders as `IS NULL`, the column is NOT NULL, so nothing matched — and the
    consent check then found no grant for brand None. Each link is NOT NULL
    with a foreign key today, so the chain cannot actually break; the point is
    that brand safety no longer rests on nullability nobody connects to it.
    """
    from app.campaigns.db_models import CampaignDB, VariantDB

    brand_id = (
        db.query(CampaignDB.brand_id)
        .join(VariantDB, VariantDB.campaign_id == CampaignDB.id)
        .filter(VariantDB.id == slot.variant_id)
        .scalar()
    )
    if brand_id is None:
        raise BrokenCampaignChain(
            f"Decision slot {getattr(slot, 'id', '?')}: variant {slot.variant_id} "
            "does not resolve to a campaign with a brand, so which brand's "
            "content and consent apply is unknown. This is a data defect, not "
            "an empty result — refusing rather than resolving nothing."
        )
    return brand_id


def takeable(db, *, brand_id: int, channel: str, language: str, needed=()) -> list:
    """The conditions on `ContentRecordDB` for a record a machine may take for
    `channel` in `language`: what a slot draws on (`candidate_query`) and what
    the variant-from-a-topic task may suggest (ADR-141 addendum 2026-10-17),
    kept in one place so the two cannot drift. `needed` are the fields its
    latest published version must fill.
    """
    from sqlalchemy import exists, func, or_

    from app.content.db_models import ContentChannelReadinessDB, ContentRecordDB, ContentVersionDB

    latest = (
        db.query(func.max(ContentVersionDB.version_number))
        .filter(ContentVersionDB.content_record_id == ContentRecordDB.id)
        .correlate(ContentRecordDB).scalar_subquery()
    )
    published_and_complete = exists().where(
        ContentVersionDB.content_record_id == ContentRecordDB.id,
        ContentVersionDB.version_number == latest,
        # Filled = holds something besides whitespace, as the readiness
        # warning and the send check read it; a JSON null or a missing key
        # gives NULL here, which is not filled either.
        *(ContentVersionDB.content[name].as_string().op("~")(r"\S") for name in needed),
    )
    return [
        ContentRecordDB.status == "active",
        # ADR-150 point 8: a decision slot resolves ONLY the sending
        # brand's content. Safe by construction — widening it is the
        # configurable filter point 10 defers, not this default. A slot
        # whose campaign chain is broken never gets here: `sending_brand_id`
        # raises rather than handing this filter None (task-18).
        ContentRecordDB.brand_id == brand_id,
        ContentRecordDB.machine_ready.is_(True),
        exists().where(ContentChannelReadinessDB.content_id == ContentRecordDB.id,
                       ContentChannelReadinessDB.channel == channel),
        published_and_complete,
        # ADR-200 point 2: in the variant's message language (its brand
        # profile's, ADR-199 point 4), or with no language set.
        or_(ContentRecordDB.language.is_(None), ContentRecordDB.language == language),
    ]


def candidate_query(db, slot, *, brand_id: int):
    """The rows a slot chooses between: `(record, category score, category id)`
    for the brand's active content, narrowed to the slot's `category_ids` when
    it names any (empty = all).

    **And only what a machine may take and the slot can render** (task-284):
    - machine ready, and marked ready for the slot's channel (ADR-179 addendum
      2026-10-05 point 3);
    - its latest published version fills every field the slot's module needs
      (ADR-174's task-284 addendum). That version is what a pick renders, so a
      record never published is no candidate. Nothing else checks a slot's
      pick: the send-time check skips slot modules (`rendering.frame.
      missing_required_in_frame`), so without this a reader gets the module
      with its headline blank. The mark and its warning are untouched.

    One row per record **and category assignment**, so a record in two
    categories appears twice — count `distinct(ContentRecordDB.id)` for how
    many records that is. Strategies add their own ordering or recipient
    filtering on top; the read-only candidate count (task-205) uses it as is,
    which is what keeps the count and the pick drawing on the same set.

    `brand_id` is the slot's sending brand (`sending_brand_id`), taken as an
    argument because each strategy also scopes its version lookup with it and
    the two must agree.
    """
    from app.campaigns.db_models import ModuleInstanceDB, VariantDB
    from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
    from app.content.service import fields_a_record_must_fill
    from app.modules.registry import get_manifest

    from app.expressions.substitute import message_language

    variant = db.get(VariantDB, slot.variant_id)
    channel = variant.channel
    language = message_language(db, variant)[1]
    # Required when shown (ADR-187 point 6): a field the module hides need not
    # be filled, so each bound module's hidden list is part of what it needs.
    bound = db.query(ModuleInstanceDB.module_type, ModuleInstanceDB.hidden_fields).filter(
        ModuleInstanceDB.decision_slot_id == slot.id)
    needed = sorted({name for t, hidden in bound if (m := get_manifest(channel, t))
                     for name in fields_a_record_must_fill(m, hidden)})
    query = (
        db.query(
            ContentRecordDB,
            ContentCategoryAssignmentDB.score,
            ContentCategoryAssignmentDB.category_id,
        )
        .join(
            ContentCategoryAssignmentDB,
            ContentRecordDB.id == ContentCategoryAssignmentDB.content_id,
        )
        .filter(*takeable(db, brand_id=brand_id, channel=channel, language=language, needed=needed))
    )
    category_ids = (slot.candidate_filter or {}).get("category_ids", [])
    if category_ids:
        query = query.filter(ContentCategoryAssignmentDB.category_id.in_(category_ids))
    return query
