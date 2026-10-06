from datetime import datetime

from typing import Any

from pydantic import BaseModel


class AudienceGroup(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    # The campaign a suggested group was derived from; null for a hand-made
    # one (task-208). It is what makes Recalculate meaningful, and the link
    # back to the campaign.
    source_campaign_id: int | None = None


class AudienceGroupListed(AudienceGroup):
    """A group as the list shows it (task-50, B26).

    `recipient_count` is the live, consent-gated audience **for
    `count_channel`**, and both are null unless the caller asked for a channel
    (ADR-176 point 5: there is no channel-less count). `pinned_count` is the
    manual pins, which a rule-only group has none of.
    """

    pinned_count: int
    recipient_count: int | None = None
    count_channel: str | None = None


class AudienceGroupCreate(BaseModel):
    name: str
    description: str | None = None


class AudienceGroupUpdate(BaseModel):
    """Only what is sent changes (task-295): leaving out the description keeps
    it, `null` clears it."""

    name: str | None = None
    description: str | None = None


class AudienceGroupMember(BaseModel):
    id: int
    group_id: int
    recipient_id: int
    added_at: datetime
    # Why they were added by hand, if anyone said, and by whom (task-295).
    reason: str | None = None
    added_by: str | None = None
    # Who they are, and — when the list was asked for a channel — the
    # exclusion rules that leave them out on it (task-297).
    external_id: str | None = None
    left_out_by: list[str] = []


class MemberAdd(BaseModel):
    reason: str | None = None


class PastePreviewRequest(BaseModel):
    text: str
    #: There is no channel-less "not agreed" (ADR-176 point 5).
    channel: str


class PasteApplyRequest(BaseModel):
    text: str
    reason: str | None = None


class PastePreview(BaseModel):
    """What pasting a list would do, before anything is added (task-295)."""

    to_add: int
    already_in: int
    not_found: list[str]
    not_agreed: int
    channel: str


class PasteResult(BaseModel):
    added: int
    already_in: int
    not_found: int


class CriteriaValues(BaseModel):
    """What a rule's language and status can be chosen from (task-295)."""

    languages: list[str]
    statuses: list[str]


class AudienceRuleBlock(BaseModel):
    """A single criteria rule inside a group.

    The group's audience is evaluated live from its blocks rather than stored
    as a frozen member list, so this is the authoring surface for who a group
    means — not a snapshot of who it currently contains.
    """

    id: int
    group_id: int
    kind: str
    criteria: dict[str, Any] | None = None
    label: str | None = None
    source: str
    position: int

    model_config = {"from_attributes": True}


class AudienceRuleBlockCreate(BaseModel):
    kind: str = "include"
    criteria: dict[str, Any] | None = None
    label: str | None = None


class AudienceRuleBlockUpdate(BaseModel):
    kind: str | None = None
    criteria: dict[str, Any] | None = None
    label: str | None = None


class BulkAddRequest(BaseModel):
    """Pins, added in one call.

    Named `recipient_ids` rather than `members` because these become manual
    pins in `AudienceGroupMemberDB` — the half of a group that is a list of
    people rather than a rule about them.
    """

    recipient_ids: list[int]


class PreviewBlock(BaseModel):
    id: int
    kind: str
    label: str | None = None
    source: str | None = None
    criteria: dict
    # The category the criteria name, resolved so a client need not look it up.
    category_name: str | None = None
    count: int


class PreviewRecipient(BaseModel):
    recipient_id: int
    external_id: str
    language: str | None = None
    status: str | None = None
    # The deliverable value on the preview's channel (an email, a device token).
    address: str | None = None


class AudienceArithmetic(BaseModel):
    """How the audience on one channel was arrived at (task-213; Manager
    Workflow interview Q4.3). The terms add up: `matched_rules − not_agreed +
    added_by_hand − removed_by_exclusion − dropped_by_consent = total`.
    `not_agreed` is a count only, among people this brand has a consent record
    with; `removed_hand_added` is the part of `removed_by_exclusion` a manager
    had added by hand. As of now: a send resolves the audience again."""

    matched_rules: int
    not_agreed: int
    added_by_hand: int
    removed_by_exclusion: int
    removed_hand_added: int
    dropped_by_consent: int
    total: int


class AudiencePreview(BaseModel):
    """What sending to a group on one channel would reach (task-50, B27).

    `reachable_count` is after the send's own exclusion stack (ADR-163's
    rider); `resolved_count - reachable_count` are the people who match and
    cannot be reached, counted by stage in `dropped_by_stage`.
    """

    group_id: int
    channel: str
    blocks: list[PreviewBlock]
    arithmetic: AudienceArithmetic
    resolved_count: int
    reachable_count: int
    unreachable_count: int
    dropped_by_stage: dict[str, int]
    # Reachable recipients matching the search (all of them with no search).
    sample_matching: int = 0
    sample: list[PreviewRecipient]


class AudienceCriteria(BaseModel):
    """Ad-hoc criteria over recipients (task-50, C11/C12). Every field narrows;
    none set means everyone consenting on the channel."""

    language: str | None = None
    status: str | None = None
    category_id: int | None = None
    min_score: float | None = None


class CriteriaPreview(BaseModel):
    """Who the criteria would add, on one channel: a count and a sample."""

    channel: str
    count: int
    sample: list[PreviewRecipient]


class BulkAddByCriteria(AudienceCriteria):
    channel: str


class BulkAddResult(BaseModel):
    matched: int
    added: int


class SuggestedAudienceRequest(BaseModel):
    campaign_id: int
