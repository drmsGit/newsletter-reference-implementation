from datetime import datetime

from pydantic import BaseModel, Field


class DeliveryExecution(BaseModel):
    id: int
    send_instance_id: int
    recipient_id: int
    status: str
    provider: str | None = None
    provider_message_id: str | None = None
    created_at: datetime
    updated_at: datetime
    # For the deliveries detail (task-50, B24): who it was, why it was not
    # sent, and when it was (ADR-183).
    recipient_external_id: str | None = None
    exclusion_reason: str | None = None
    sent_at: datetime | None = None
    # Which channel and purpose this delivery was (task-208): without them a
    # client cannot tell an email delivery from a push one. Both NOT NULL.
    channel: str | None = None
    purpose: str | None = None


class DeliveryExecutionCreate(BaseModel):
    send_instance_id: int
    recipient_id: int
    status: str = "created"
    provider: str | None = None
    provider_message_id: str | None = None


class SendInstance(BaseModel):
    id: int
    snapshot_id: int
    name: str
    status: str
    provider: str | None = None
    scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Exposed 2026-10-01 for the deliveries screen (task-28) — the columns
    # existed and the response dropped them, task-208's pattern. The counts are
    # derived from the executions once a send finishes, so they read 0 before
    # it has run.
    from_address: str | None = None
    audience_group_id: int | None = None
    sent_count: int = 0
    failed_count: int = 0
    excluded_count: int = 0
    #: ADR-192: a send still "sending" with no activity for 30 minutes — likely
    #: left by a process that died. Flagged, never released automatically; a
    #: person releases it (POST .../release). `last_activity_at` is the newest
    #: change to the send or any of its executions, set for "sending" sends.
    stranded: bool = False
    last_activity_at: datetime | None = None
    # "Don't send to someone who would get no content record", chosen at plan
    # time (task-228; its meaning corrected in the ADR-086 addendum 2026-10-11).
    skip_without_resolution: bool = False


class SendPlanRequest(BaseModel):
    """Plan a send from a snapshot and an audience group (task-49, C8).

    The JSON twin of the Jinja plan form. No `audience_resolution_mode`: every
    send re-resolves its audience before it fires (ADR-176 point 4), so there
    is nothing to choose.
    """

    # The column is String(255); longer used to reach the database and 500.
    name: str = Field(min_length=1, max_length=255)
    audience_group_id: int
    provider: str = "mock"
    from_address: str | None = None
    # Omitted: a draft, fired later by hand. Given: status "scheduled".
    scheduled_at: datetime | None = None
    # "Don't send to someone who would get no content record" (ADR-086
    # addenda 2026-10-08 and 2026-10-11): skip a recipient for whom no
    # content record shows — every personalised block came up empty and none
    # is placed by hand. Off by default.
    skip_without_resolution: bool = False


class SendInstanceListed(SendInstance):
    """A send as the deliveries list shows it (task-50, B23): what it sent, and
    live counts — the stored sent/failed/excluded read 0 until a send finishes."""

    campaign_id: int | None = None
    campaign_name: str | None = None
    variant_id: int | None = None
    variant_name: str | None = None
    execution_count: int = 0
    event_count: int = 0


class SendInstanceDetail(SendInstance):
    """One send, and what explains the gap between what it planned and what
    it sent — the Manager Workflow interview's question 5.5.

    Because every send re-resolves its audience before it fires (ADR-176 point
    4), exclusions are routine, not an edge case: a manager who approved 1,104
    and sees 1,098 sent needs the answer, not a discrepancy. So the detail
    carries the execution total and the exclusions counted by stage of the
    ADR-163 point 7 stack — addressability, consent, suppression.
    """

    execution_count: int
    exclusions_by_stage: dict[str, int]
    audience_group_name: str | None = None


class SendInstanceCreate(BaseModel):
    snapshot_id: int
    name: str
    status: str = "draft"
    provider: str | None = None
    scheduled_at: datetime | None = None

class TestSendRequest(BaseModel):
    """One real email to one typed address.

    `variant_id` is optional: without it a plain test body goes, which is the
    question "does mail leave the building at all" asked on its own. With it,
    the variant is rendered through the email path — and if that fails the send
    still happens with `render_note` explaining what the recipient got instead.
    """

    to: str
    subject: str = "Test from the newsletter reference build"
    provider: str = "resend"
    variant_id: int | None = None
    recipient_id: int | None = None


class PlannedTestRequest(BaseModel):
    """A test of a planned send (task-67): the frozen email, as `recipient_id`
    would get it, to one typed address."""

    to: str = Field(min_length=3, max_length=320)
    recipient_id: int | None = None


class RecipientsNow(BaseModel):
    """What a send would go to if fired now (task-67; ADR-183 addendum
    2026-10-12): who is still to be mailed, counted the way the send counts
    them, against the company's cap."""

    send_instance_id: int
    status: str
    recipients: int
    cap: int
    provider: str
    provider_label: str
    reaches_real_inboxes: bool
    from_address: str | None = None
    scheduled_at: datetime | None = None


class TestSendResponse(BaseModel):
    """What one test send did, as the API answers it.

    **Named `...Response`, not `...Result`, deliberately.**
    `delivery.service.TestSendResult` is the dataclass this mirrors, and
    the router imports from both modules — a shared name would shadow one
    silently. `app/rendering/router.py` carries a comment about the 500
    that shape already caused once.
    """

    success: bool
    to: str
    provider: str
    provider_message_id: str | None = None
    message: str | None = None
    #: Set when the chosen variant could not be rendered and a plain body went
    #: instead. **Not an error** — the send still happened.
    render_note: str | None = None


class ProcessDueResult(BaseModel):
    """What firing the due scheduled sends did."""

    triggered: int
    send_instance_ids: list[int] = []
    #: Due sends held for a person because they were above the calling
    #: integration's unattended ceiling (task-341). Still scheduled.
    held_send_instance_ids: list[int] = []


class ReconstructedModule(BaseModel):
    module_id: int
    module_type: str
    # content | static | slot | empty | unknown
    kind: str
    # A slot's pick, 1 first: a slot shows up to five, one row each (task-109).
    rank: int | None = None
    content_record_id: int | None = None
    content_version_id: int | None = None
    override_id: int | None = None
    decision_resolution_id: int | None = None


class DeliveryAsSent(BaseModel):
    """What one recipient got, as of the send date (ADR-183). Content is exact;
    `templates_match` and `hash_matches` say whether the layout is too."""

    execution_id: int
    send_instance_id: int
    recipient_id: int
    channel: str
    sent_at: datetime | None = None
    envelope: dict
    # Email: the HTML. Push: `fields`.
    body: str | None = None
    fields: dict | None = None
    modules: list[ReconstructedModule]
    templates_match: bool
    hash_matches: bool


class TraceContribution(BaseModel):
    category_id: int
    category_name: str
    base_weight: float
    contribution_type: str


class TraceEvent(BaseModel):
    id: int
    event_type: str
    occurred_at: datetime
    event_data: dict | None = None
    # What this event taught the recipient's profile (ADR-132): nothing, when
    # it named no content (ADR-182).
    contributions: list[TraceContribution]


class ExecutionTrace(BaseModel):
    """One execution's engagement and what it learned (task-50, B24)."""

    execution_id: int
    events: list[TraceEvent]
