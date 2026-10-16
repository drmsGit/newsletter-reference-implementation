from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class ContentField(BaseModel):
    """One field a content record can carry — ADR-177's descriptor.

    `required` is absent on purpose: it belongs to *(module, field)*, so a
    client asking "must I fill this?" has to name a module and ask `GET
    /modules`. Reporting one answer here would be reporting the wrong one.
    """

    name: str
    #: What a form calls it, written once in `storage/fields.json` (ADR-177
    #: addendum 2026-10-04).
    label: str | None = None
    concept: str | None = None
    size: str | None = None
    type: str = "text"
    note: str | None = None
    channel: str | None = None
    envelope: bool = False
    #: For an `image` field, the field that holds the alt text of a web
    #: address; a form shows it with the address, not as a field of its own
    #: (ADR-197 addendum 2026-10-15, the second).
    alt: str | None = None


class ContentRecord(BaseModel):
    id: int
    title: str
    description: str | None = None
    content: dict[str, Any]
    status: str = "active"
    # The version token a write states in If-Match (task-257).
    updated_at: datetime | None = None


class ChannelReadiness(BaseModel):
    """A record marked ready for one channel (ADR-174; task-283): who and when,
    and the warning when the record can fill no module of that channel — said
    by the server, so no client works it out (ADR-177)."""

    channel: str
    marked_by: str | None = None
    marked_at: datetime
    warning: str | None = None


class MachineReady(BaseModel):
    machine_ready: bool


class ContentListItem(ContentRecord):
    """One row of `GET /content/`, with what the bind picker's "not published
    yet" notice needs (task-268, task-263 decision 6).

    `None` means no version was ever published, so a send would refuse the
    record (`UnpublishedContentError`). Whether the live content differs from
    the latest version is the detail's `unpublished_changes`, not a list
    concern: binding such a record is fine, a send uses the published version.
    """

    latest_version_number: int | None = None
    #: The channels this record is marked ready for (task-283).
    ready_for: list[str] = []


class ContentRecordDetail(ContentRecord):
    """One record, with whether a send would use what it says now (task-257).

    A send renders the latest *published* version, not the live record
    (`rendering.service.resolve_renderable_content`), so an edit reaches the
    next send only once it is published. The variant editor says so beside a
    catalogue field, with a Publish button (design pass D5).
    """

    latest_version_number: int | None = None
    # True when the live content differs from the latest version, or when
    # nothing has been published yet.
    unpublished_changes: bool
    #: ADR-179 point 2: may a machine pick this without a person deciding?
    machine_ready: bool = False
    #: The channels a person marked it ready for, each with its warning (ADR-174).
    readiness: list[ChannelReadiness] = []


class ContentCreate(BaseModel):
    title: str
    description: str | None = None
    content: dict[str, Any]


class ContentPatch(BaseModel):
    """A partial edit that honours what the caller was offering.

    **`groups` is the field this exists for.** An absent field and a cleared
    one are indistinguishable in a dict, so a client that renders push fields
    only when push is enabled would erase push copy on every edit made while
    it was off — unless it can say which groups it was authoritative for.
    The Jinja form has carried that signal since 2026-09-17 as
    `channel_sections_present`; this is the same signal on the JSON plane.

    Omitting `groups` merges nothing and is a no-op on `content`, which is the
    safe default: a caller that has not said what it was offering has not
    earned the right to clear anything.
    """

    title: str | None = None
    description: str | None = None
    content: dict[str, Any] = {}
    #: Names from `content.service.content_field_groups()` — "email", "push".
    groups: list[str] = []
    #: The AI draft run these fields were taken from (task-368): the audit
    #: entry names it when it is this record's draft run.
    applied_suggestion_run_id: int | None = None


class ContentStatusUpdate(BaseModel):
    status: str


class Category(BaseModel):
    id: int
    name: str
    type: str = "main"


class CategoryCreate(BaseModel):
    name: str
    type: str = "main"


class CategoryChange(BaseModel):
    """Rename a category or change its type; what is left out stays."""

    name: str | None = None
    type: str | None = None


class ContentCategoryAssignment(BaseModel):
    id: int
    content_id: int
    category_id: int
    score: int = 10


#: A category score: 1 (barely in the category) to 10 (squarely) — ADR-080's
#: 2026-10-04 addendum. Stated on the request models so the API refuses with a
#: field error (422) a form can show, before the database's own CHECK would.
SCORE_MIN, SCORE_MAX = 1, 10


class ContentCategoryAssignmentCreate(BaseModel):
    category_id: int
    score: int = Field(10, ge=SCORE_MIN, le=SCORE_MAX)
    #: Taken from an AI draft run (task-368); named in the audit entry.
    applied_suggestion_run_id: int | None = None


class ContentCategoryAssignmentScore(BaseModel):
    """Change an assignment's score in place (task-278), so the record never
    drops out of the category the way remove-and-re-add made it."""

    score: int = Field(ge=SCORE_MIN, le=SCORE_MAX)
    applied_suggestion_run_id: int | None = None


class ContentDraftRequest(BaseModel):
    """What the AI drafts from (task-368; ADR-141 addendum 2026-10-16). The
    source goes to the model and is never stored."""

    source: str = Field(description="Pasted text or a brief; at most 12,000 characters")
    channels: list[str] = Field(description="The channels whose text fields are drafted")


class ContentDraftStarted(BaseModel):
    ai_run_id: int
    status: str
    message: str | None = None


class DraftedField(BaseModel):
    name: str
    label: str
    channel: str | None = None
    text: str
    #: What the record holds in this field now; "" when empty.
    current: str


class ProposedCategory(BaseModel):
    category_id: int
    name: str
    score: int
    reason: str
    #: The record's own score for it, when it is already assigned.
    assigned_score: float | None = None
    assignment_id: int | None = None


class ContentDraft(BaseModel):
    """One AI draft run for a record, read back (task-368)."""

    run_id: int
    status: str
    created_at: datetime
    provider: str
    model: str | None = None
    prompt_version: int | None = None
    input_tokens: int
    output_tokens: int
    fields: list[DraftedField]
    categories: list[ProposedCategory]
    #: What a manager must know before taking any of it (what was left out,
    #: a truncated reply).
    notices: list[str]
    reply: str
    message: str | None = None


class ContentVersion(BaseModel):
    id: int
    content_record_id: int
    version_number: int
    content: dict[str, Any]
    created_by: str | None = None
    created_at: datetime


class ContentVersionCreate(BaseModel):
    """Publish a record's current content as its next version. **No author
    field**: who published is the caller, set by the server (the task-243 rule,
    applied here 2026-10-03). A body still sending `created_by` is not refused;
    the value is ignored."""

    content_record_id: int


class CategoryRelation(BaseModel):
    id: int
    parent_category_id: int
    child_category_id: int
    relation_type: str = "parent_child"
    created_at: datetime


class CategoryRelationCreate(BaseModel):
    parent_category_id: int
    child_category_id: int
    relation_type: str = "parent_child"

class ContentDuplicate(BaseModel):
    target_brand_id: int


class ContentDuplicateTarget(BaseModel):
    """A brand this caller may copy a record into (task-50, B14)."""

    id: int
    name: str
    crossing: bool


class ContentAssignment(BaseModel):
    """One category on a record, with what removing it needs (task-50, B17/C5)."""

    assignment_id: int
    category_id: int
    name: str
    type: str
    score: float | None = None


class ContentResolutionUse(BaseModel):
    id: int
    decision_slot_id: int
    recipient_id: int | None = None
    content_version_id: int | None = None
    score: float | None = None
    reason: str | None = None
    created_at: datetime


class ContentSignal(BaseModel):
    recipient_id: int
    category_id: int
    category_name: str
    base_weight: float
    contribution_type: str
    created_at: datetime


class ContentUsage(BaseModel):
    """Where a record was picked and what its engagement taught (task-50, B17)."""

    resolutions: list[ContentResolutionUse]
    signals: list[ContentSignal]


class ContentFigures(BaseModel):
    """A record's figures (task-359; ADR-196 addendum 2026-10-16), counted per
    delivery, all time: the campaign results' definitions, per record."""

    deliveries: int = Field(description="Sent deliveries that carried the record")
    picked: int = Field(description="Of those, how many carried it through a slot pick")
    clicks: int = Field(description="Clicks on its links")
    unique_clickers: int = Field(description="Deliveries with at least one click on it")
    clicks_in_deliveries: int = Field(description="All clicks in the deliveries that carried it")
    click_share: float | None = Field(description="clicks / clicks_in_deliveries; None while those have none")


class CampaignFigures(BaseModel):
    campaign_id: int
    campaign_name: str
    figures: ContentFigures


class ContentPerformance(BaseModel):
    overall: ContentFigures
    by_campaign: list[CampaignFigures]


class UnsentCampaign(BaseModel):
    id: int
    name: str


class CampaignVariantUse(BaseModel):
    id: int
    name: str
    channel: str
    #: The monitoring screen's stage (task-216); "sent" marks a sent variant.
    stage: str


class ContentCampaign(BaseModel):
    """A campaign with a module bound to the record, and the variants of it
    that use the record (task-267)."""

    id: int
    name: str
    variants: list[CampaignVariantUse]


class ContentReach(BaseModel):
    """Which unsent campaigns use a record (task-224, ADR-178 point 8): the
    count the composer shows beside a catalogue field, and the list behind it.
    Ids and names only — the composer reports scope, not people."""

    count: int
    campaigns: list[UnsentCampaign]
