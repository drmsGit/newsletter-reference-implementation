from datetime import datetime
from pydantic import BaseModel
from typing import Literal, Any

# Module-scope is safe: `app.ai.orchestration` imports nothing from `app`
# at module scope, so this cannot cycle.
from app.ai.orchestration import Outcome


class Variant(BaseModel):
    id: int
    campaign_id: int
    # ADR-160 point 4. Fixed at creation (point 5), so there is no setter for
    # it anywhere and `VariantUpdate` deliberately does not carry it.
    channel: str
    name: str
    subject: str | None = None
    preheader: str | None = None
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class VariantCreate(BaseModel):
    channel: str = "email"
    name: str = "Variant A"
    subject: str | None = None
    preheader: str | None = None
    # `campaigns.service.VARIANT_STATUSES` (task-203). The read model `Variant`
    # keeps `str`, since rows written before the rule may hold other values.
    status: Literal["draft", "ready"] = "draft"


class VariantUpdate(BaseModel):
    name: str
    subject: str | None = None
    preheader: str | None = None


class Campaign(BaseModel):
    id: int
    name: str
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    name: str
    # The channel of the initial variant this creates, not a property of the
    # campaign — ADR-160 point 4 keeps channel off the campaign. Defaulted here
    # and only here: an unauthenticated machine caller has no session to have
    # chosen from, while `create_campaign` itself still refuses to guess.
    channel: str = "email"
    status: str = "draft"
    initial_variant_name: str = "Variant A"


class CampaignWithVariants(Campaign):
    variants: list[Variant]


class ModuleInstance(BaseModel):
    id: int
    variant_id: int
    module_type: str
    position: int
    content_record_id: int | None = None
    module_data: dict[str, Any] | None = None
    decision_slot_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ModuleInstanceCreate(BaseModel):
    module_type: str
    content_record_id: int | None = None
    module_data: dict[str, Any] | None = None
    decision_slot_id: int | None = None


class DecisionSlot(BaseModel):
    id: int
    variant_id: int
    name: str
    decision_type: str
    decision_strategy: str
    candidate_filter: dict[str, Any] | None = None
    strategy_config: dict[str, Any] | None = None
    max_results: int = 1
    created_at: datetime
    updated_at: datetime


class DecisionSlotCreate(BaseModel):
    name: str
    decision_type: str = "content_recommendation"
    decision_strategy: str = "top_score"
    candidate_filter: dict[str, Any] | None = None
    strategy_config: dict[str, Any] | None = None
    max_results: int = 1


class ModuleInstanceUpdate(BaseModel):
    """Edit a module in place.

    Mirrors `ModuleInstanceCreate` minus `position`, which moves through its
    own endpoint because reordering is a different act from editing and has a
    uniqueness constraint of its own.
    """

    module_type: str
    content_record_id: int | None = None
    module_data: dict[str, Any] | None = None
    decision_slot_id: int | None = None


class DecisionSlotPatch(BaseModel):
    """A partial edit: what is not sent is left as it is.

    **The section that matters is `strategy_config`.** `recipient_top_score`
    declares two tunable weights with defaults, and `_normalize_section` fills
    a declared key that is absent with its default — so replacing the section
    wholesale is not "leave it alone", it is "reset it". A client editing the
    candidate filter with `PUT` silently undoes whatever a manager tuned.

    **Absent and `null` are different here**, and Pydantic's `model_fields_set`
    is what tells them apart: omitting `strategy_config` keeps the stored one,
    sending `null` clears it. A single `| None = None` could not express both,
    which is the reason this model exists rather than reusing the PUT one.
    """

    decision_strategy: str | None = None
    candidate_filter: dict | None = None
    strategy_config: dict | None = None

    def sent(self, field: str) -> bool:
        """Whether the caller actually sent this field, null or not."""
        return field in self.model_fields_set


class DecisionSlotUpdate(BaseModel):
    """Edit a slot's strategy and configuration.

    `name`, `decision_type` and `max_results` are deliberately absent: the
    service updates strategy, candidate filter and config only, and accepting
    fields it will silently drop would be worse than not offering them.
    """

    decision_strategy: str
    candidate_filter: dict[str, Any] | None = None
    strategy_config: dict[str, Any] | None = None


class DecisionResolution(BaseModel):
    id: int
    decision_slot_id: int
    recipient_id: int | None = None
    content_record_id: int
    content_version_id: int | None = None
    reason: str | None = None
    score: float | None = None
    created_at: datetime


class DecisionResolutionCreate(BaseModel):
    recipient_id: int | None = None
    content_record_id: int
    content_version_id: int | None = None
    reason: str | None = None
    score: float | None = None


class SubjectSuggestionResult(BaseModel):
    """The outcome of an AI subject/preheader suggestion (ADR-141 §3 Mode A).

    `outcome` reuses `app.ai.orchestration.Outcome` rather than restating the
    vocabulary, so the generated client cannot drift from the service that
    produces it. The refused outcomes never reach here — they are raised as a
    409 — but they stay in the type because the union is the service's, not
    this route's.
    """

    outcome: Outcome
    message: str | None = None
    #: The persisted run. The options are read back from it; they are not
    #: returned here, because the run row is the record.
    ai_run_id: int | None = None
    #: The held request, for the approval case.
    pending_action_id: int | None = None


class CampaignDuplicate(BaseModel):
    """Duplicate a campaign, possibly into another brand (task-50).

    `content_mode` is one of `keep` (same brand: modules cite the same
    records), `copy` (other brand: records are duplicated across) or `layout`
    (either: modules arrive unbound). The boundary decides which are legal —
    `GET`-ing the wizard's options is not needed, a wrong one is refused 409.
    """

    name: str
    target_brand_id: int
    content_mode: str
    # Omitted means every variant; an explicitly empty list is refused.
    variant_ids: list[int] | None = None


class CampaignDuplicated(BaseModel):
    campaign_id: int
    source_campaign_id: int
    source_brand_id: int
    target_brand_id: int
    content_mode: str
    crossed_brands: bool
    variants: int
    modules: int
    decision_slots: int
    # source content record id -> the copy's id. Empty unless `copy`.
    content_records_copied: dict[int, int]
    url_carriers: list[str]


class DuplicationVariantSummary(BaseModel):
    id: int
    name: str
    channel: str
    modules: int
    decision_slots: int


class DuplicationSummary(BaseModel):
    variants: list[DuplicationVariantSummary]
    module_count: int
    decision_slot_count: int
    content_titles: list[str]


class DuplicationTarget(BaseModel):
    id: int
    name: str
    crossing: bool
    # The content modes this caller may use for this target, in UI order.
    modes: list[str]


class DuplicationOptions(BaseModel):
    """What the duplicate wizard offers (task-50, B14) — computed by the
    server so a client never rebuilds the boundary rule."""

    source_brand_id: int
    summary: DuplicationSummary
    # Summarising only the chosen variants, so the content count a manager sees
    # is the one the copy will produce. Equals `summary` when none are chosen.
    selected_summary: DuplicationSummary
    targets: list[DuplicationTarget]


class SuggestionOption(BaseModel):
    subject: str
    preheader: str


class SuggestionRun(BaseModel):
    """One AI suggestion run for a variant, read back (task-50, C7)."""

    run_id: int
    status: str
    created_at: datetime
    provider: str
    model: str | None = None
    prompt_version: int | None = None
    input_tokens: int
    output_tokens: int
    options: list[SuggestionOption]
    # What a manager must be told before using an option (truncation, fewer
    # options than asked for).
    notices: list[str]
    reply: str
    message: str | None = None


class DecisionSlotListed(BaseModel):
    """A decision slot in the brand, with what it has done (task-50, B21)."""

    id: int
    name: str
    decision_type: str
    decision_strategy: str
    variant_id: int
    variant_name: str
    campaign_id: int
    campaign_name: str
    resolution_count: int
    unique_content_count: int
    last_resolution_at: datetime | None = None


class SlotSummary(BaseModel):
    resolution_count: int
    unique_recipient_count: int
    unique_content_count: int
    avg_score: float
    min_score: float
    max_score: float
    last_resolution_at: datetime | None = None


class SlotTopContent(BaseModel):
    content_id: int
    title: str
    version_number: int | None = None
    selection_count: int
    # Percent of this slot's resolutions.
    share: float


class SlotResolution(BaseModel):
    id: int
    recipient_id: int | None = None
    content_record_id: int
    content_title: str
    content_version: int | None = None
    score: float | None = None
    reason: str | None = None
    created_at: datetime


class SlotReason(BaseModel):
    reason: str | None = None
    count: int


class DecisionSlotStats(BaseModel):
    """One slot and what it has picked (task-50, B22)."""

    slot: DecisionSlot
    variant_id: int
    variant_name: str
    campaign_id: int
    campaign_name: str
    summary: SlotSummary
    top_content: list[SlotTopContent]
    latest: list[SlotResolution]
    reasons: list[SlotReason]
