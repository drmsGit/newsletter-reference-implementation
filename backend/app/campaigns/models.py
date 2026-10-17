from datetime import datetime
from pydantic import BaseModel, Field
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
    # The envelope copy: the fields the channel's manifest declares as
    # envelope (ADR-162 point 1), by name — `{"subject", "preheader"}` for
    # email, `{}` for push, which has none. A map rather than `subject` and
    # `preheader` (task-48): those are email's field names, and every variant
    # of every channel answered with them.
    envelope: dict[str, str] = {}
    status: str = "draft"
    # The brand profile it uses (ADR-194 point 4). None only on rows built
    # outside the services, which read as the brand's default.
    brand_profile_id: int | None = None
    # Set when its profile was deleted and it fell back to the default;
    # cleared when a manager picks one (ADR-194 point 1).
    brand_profile_notice: str | None = None
    created_at: datetime
    updated_at: datetime


class VariantCreate(BaseModel):
    channel: str = "email"
    name: str = "Variant A"
    # Fields the channel does not declare are ignored, as `set_envelope_fields` does.
    envelope: dict[str, str | None] | None = None
    # `campaigns.service.VARIANT_STATUSES` (task-203). The read model `Variant`
    # keeps `str`, since rows written before the rule may hold other values.
    status: Literal["draft", "ready"] = "draft"
    # One of the working brand's profiles; left out, the brand's default.
    brand_profile_id: int | None = None


class VariantUpdate(BaseModel):
    name: str
    # Replaces the whole envelope when sent; left out, the envelope is untouched.
    # A blank field clears it.
    envelope: dict[str, str | None] | None = None
    # One of the working brand's profiles; left out, the profile stays as it
    # is. Picking one clears the fallback notice.
    brand_profile_id: int | None = None
    # The AI suggestion run this envelope was taken from (task-367): said in
    # the audit entry, as the Jinja page's "applied suggestion" is. Only a run
    # of this variant counts.
    applied_suggestion_run_id: int | None = None


class Campaign(BaseModel):
    id: int
    name: str
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


class MonitoredVariant(BaseModel):
    id: int
    name: str
    channel: str
    # sending | scheduled | planned | snapshotted | sent | composing
    stage: str
    has_failures: bool


class MonitoredCampaign(BaseModel):
    """Where one campaign is, derived from its variants (task-216)."""

    id: int
    name: str
    # in_flight | in_preparation | sent
    state: str
    has_failures: bool
    next_scheduled_at: datetime | None = None
    last_sent_at: datetime | None = None
    updated_at: datetime
    variants: list[MonitoredVariant]


class ResultFigures(BaseModel):
    """A variant's or a campaign's figures (task-58, ADR-196 points 3 and 4).

    Counted per delivery: "unique" is distinct deliveries with at least one
    such event. `delivered` is None where the channel reports no deliveries
    (push). `click_rate` is unique clickers over sent, None when nothing was
    sent. Opens are not a figure (task-353)."""

    recipients: int
    sent: int
    delivered: int | None = None
    failed: int
    excluded: int
    excluded_by_stage: dict[str, int] = {}
    bounced: int
    complaints: int
    clicks_total: int
    unique_clickers: int
    click_rate: float | None = None
    unsubscribes: int


class VariantResults(ResultFigures):
    id: int
    name: str
    channel: str


class CampaignResults(BaseModel):
    """The campaign page's results section. Empty until a send has gone out."""

    campaign: ResultFigures | None = None
    variants: list[VariantResults]
    # Unsubscribes record their delivery only since this moment; a send older
    # than it may have had more than it shows (ADR-196 point 6).
    unsubscribes_counted_since: datetime
    unsubscribes_partial: bool


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
    # The fields a manager hid in this module (ADR-187); set only through
    # `PUT /campaigns/modules/{id}/hidden-fields`.
    hidden_fields: list[str] = []
    created_at: datetime
    updated_at: datetime


class HiddenFields(BaseModel):
    """The fields to hide in a module — the whole list; `[]` shows them all."""

    hidden_fields: list[str]


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
    # "Show up to": 1-5 picks, best first; a push slot is always 1 (ADR-084
    # addendum 2026-10-11).
    max_results: int = Field(1, ge=1, le=5)


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
    # "Show up to" (task-109): editable now that something reads it.
    max_results: int | None = Field(None, ge=1, le=5)

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
    """The outcome of an AI subject/preheader suggestion (ADR-141 §3, Assistive AI).

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
    # Active overrides reproduced on the copy, and ones LAYOUT dropped because
    # their module arrived unbound (task-113).
    overrides_carried: int = 0
    overrides_not_carried: int = 0


class VariantDuplicate(BaseModel):
    """Duplicate one variant inside its brand (task-229). Every field optional.

    `target_campaign_id` omitted means the variant's own campaign. `content_mode`
    omitted means the default for that target: `keep` inside the own campaign
    (an A/B arm), `layout` into another one (the weekly newsletter).
    `copy` is refused, because a variant copy never leaves its brand.
    """

    target_campaign_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    content_mode: str | None = None


class VariantDuplicated(BaseModel):
    variant_id: int
    source_variant_id: int
    campaign_id: int
    source_campaign_id: int
    content_mode: str
    modules: int
    decision_slots: int
    url_carriers: list[str]
    overrides_carried: int = 0
    overrides_not_carried: int = 0


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
    pending_action_id: int | None = Field(
        default=None,
        description="The approval this run waits on (or went through): its options are taken there, not in the editor",
    )


class TopicRequest(BaseModel):
    """What the variant is about (task-370); sent to the model, not stored."""

    topic: str = Field(description="At most 500 characters")


class ProposedRecord(BaseModel):
    record_id: int
    title: str
    reason: str


class ProposedSlot(BaseModel):
    category_ids: list[int]
    categories: list[str]
    reason: str


class TopicProposal(BaseModel):
    """One proposal for an empty variant, read back (task-370; ADR-141 addendum 2026-10-17)."""

    run_id: int
    status: str
    created_at: datetime
    provider: str
    model: str | None = None
    prompt_version: int | None = None
    input_tokens: int
    output_tokens: int
    #: How many records the model chose among (the newest takeable ones).
    offered: int
    hero: ProposedRecord | None = None
    editorial: str
    blocks: list[ProposedRecord]
    slot: ProposedSlot | None = None
    subject: str
    preheader: str
    notices: list[str]
    reply: str
    message: str | None = None


class BuildFromProposal(BaseModel):
    """The ticked parts of one proposal. Left out (null), a part is taken as proposed."""

    run_id: int
    hero: bool = True
    #: The editorial text as edited; "" leaves the block out; null takes the proposal's.
    editorial: str | None = None
    #: The ticked blocks' record ids, in order; null takes all proposed.
    blocks: list[int] | None = None
    slot: bool = True
    envelope: bool = True


class BuiltFromProposal(BaseModel):
    built: int


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
    # The version token a write sends back in If-Match (task-110).
    updated_at: datetime


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


class SlotCandidates(BaseModel):
    """What a slot would choose between right now, without choosing (task-205).

    Counted over the same query the strategies pick from
    (`decision.strategies.base.candidate_query`); asking writes nothing.
    """

    slot_id: int
    # Distinct content records: the brand's active content in the slot's categories.
    candidate_count: int
    # The category filter applied; empty means every category.
    category_ids: list[int]
    # The strategy declares it picks per recipient. Such a strategy may draw
    # from fewer than `candidate_count` for any one person — the recipient
    # top score keeps only categories that person has a signal for.
    requires_recipient: bool


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


class ActiveOverride(BaseModel):
    id: int
    field_overrides: dict
    overridden_by: str | None = None
    reason: str | None = None


class ComposedModule(BaseModel):
    id: int
    position: int
    module_type: str
    content_record_id: int | None = None
    decision_slot_id: int | None = None
    # What a manager reads instead of the ids (2026-10-04).
    content_record_title: str | None = None
    decision_slot_name: str | None = None
    module_data: dict
    # The fields a manager hid in this module (ADR-187).
    hidden_fields: list[str] = []
    # False when no manifest exists for this type on this channel.
    known: bool
    # A manager may override its fields (content-bound, never a slot).
    overrideable: bool
    active_override: ActiveOverride | None = None
    # The version token a write sends back in If-Match (task-110).
    updated_at: datetime


class VariantFence(BaseModel):
    """Who last edited a variant, and whether that still holds machines off
    (ADR-180 and its 2026-10-04 addendum, task-254). Lapsed or not, it is
    "last edited by X at HH:MM"; `active` says whether it is a fence."""

    by: str | None = None
    by_type: str | None = None
    at: datetime
    active: bool


class ComposedBrandProfile(BaseModel):
    """The profile a variant uses, as the editor shows it (task-350)."""

    id: int
    name: str
    language: str
    kind: str
    is_default: bool
    missing: list[str] = Field(description="Required fields the profile still lacks")
    notice: str | None = Field(None, description="Why it changed without the manager choosing it")


class ComposedVariant(BaseModel):
    variant: Variant
    brand_profile: ComposedBrandProfile
    fence: VariantFence | None = None
    # None: the channel sets no limit.
    module_limit: int | None = None
    can_add_module: bool
    has_envelope: bool
    #: "Prepare from a topic" is offered: an email variant with no content
    #: blocks yet (task-370; ADR-141 addendum 2026-10-17).
    preparable_from_topic: bool = False
    accepted_module_types: list[str]
    modules: list[ComposedModule]
    # The subject/preheader module, kept apart from the body (ADR-162 point 1).
    envelope_modules: list[ComposedModule]
    decision_slots: list[DecisionSlotListed]


class CampaignComposition(BaseModel):
    """A campaign as the variant editor shows it (task-50, B11)."""

    campaign: Campaign
    variants: list[ComposedVariant]


class SlotAttach(BaseModel):
    """Fill a catalogue module from a new decision slot (task-264). The
    strategy's declared settings start at their defaults and are edited on
    the slot afterwards."""

    decision_strategy: str = "top_score"


class SlotAttached(BaseModel):
    """The module, now bound to the new slot, and the slot. The module's
    `updated_at` is the version its next write states."""

    module: ModuleInstance
    slot: DecisionSlot
