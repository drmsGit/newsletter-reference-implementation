from datetime import datetime
from pydantic import BaseModel
from typing import Any

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
    status: str = "draft"


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
