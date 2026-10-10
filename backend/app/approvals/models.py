"""What the JSON plane says about a held action.

Deliberately not a projection of `PendingActionDB`. A pending row carries a
`payload` — an open dict the action author controls — and ADR-153 §5 binds what
may be published about an action. So the payload never leaves the server; what
a caller gets is the **frozen summary**, the **live description** the action
computes for a reviewer, and the lifecycle facts.
"""
from datetime import datetime

from pydantic import BaseModel


class PendingActionRow(BaseModel):
    """One row of the inbox."""

    id: int
    action_key: str
    label: str
    summary: str
    #: `effective_status`, not the stored column. The column is a cache of the
    #: latest audit entry and is only eventually consistent with `expires_at` —
    #: no scheduler is required — so a list that rendered the column would show
    #: "pending" for a request that has in fact lapsed.
    status: str
    brand_id: int | None
    requested_by_type: str
    requested_by_id: int | None
    created_at: datetime
    # None for an action type that declares no deadline: it never expires (task-210).
    expires_at: datetime | None = None
    decided_at: datetime | None
    # What is being decided, so a client can link to it (task-208), and who
    # decided it and why, for decision history. Exposed since 2026-10-03.
    # **`payload` is not here, deliberately**: it is the action's internal
    # arguments, and the detail's `rows` are its readable description.
    subject_type: str | None = None
    subject_id: int | None = None
    decided_by_type: str | None = None
    decided_by_id: int | None = None
    decision_reason: str | None = None
    # Readable names for both actors (2026-10-03), so the inbox and the
    # decision history read without a lookup. `decided_by_name` is None when
    # nobody decided — an expired request.
    requested_by_name: str | None = None
    decided_by_name: str | None = None
    # Whether the requester is still allowed to raise this request (task-331):
    # False means approving will withdraw it and nothing will run. Set only on
    # a request still waiting; None once decided, or for a requester with no
    # standing to lose (a system sweep).
    requester_allowed: bool | None = None
    # What an approved action ended in, as it stands now (task-338): an
    # approved send's "Partial failed: 940 delivered, 60 failed, 0 excluded."
    # From the action's optional `outcome` hook, read live; None for a request
    # that did not run, or an action that offers no outcome.
    outcome: str | None = None


class DescriptionRow(BaseModel):
    label: str
    value: str


class DecisionOption(BaseModel):
    """One option of a pick-one (ADR-141 §4). `index` is what approve takes."""

    index: int
    label: str


class PendingActionDetail(PendingActionRow):
    """The review surface: what the frozen line said, and what is true now.

    Both, because they answer different questions. `summary` is what the
    requester was told and survives its subject being deleted; `rows` is
    recomputed on every read, so the count a reviewer sees is the count that
    would be mailed rather than the one that applied when it was queued.
    """

    rows: list[DescriptionRow] = []
    #: Set when the action refuses to run — an advisory to the client, never
    #: the enforcement. `approve` still refuses on its own, because a disabled
    #: button is a courtesy and not a control.
    blocked_reason: str | None = None
    #: Populated when `describe()` itself raised. A description that blows up
    #: must not hide the request: the reviewer still needs to see something is
    #: waiting and still needs to be able to reject it.
    describe_error: str | None = None
    #: Whether *this* caller may decide *this* row — the action's own
    #: `approve_permission`, checked against the row's brand.
    may_decide: bool = False
    # Why a held action failed to run, when it did: on the detail only, not on
    # every inbox row. The approver already sees this text when they decide.
    execution_error: str | None = None
    # From the action's live description: what should give the approver pause
    # (rendered, never enforced), and the options of a pick-one, without which
    # an action that refuses to run without a choice could not be approved
    # from the JSON plane at all.
    warnings: list[str] = []
    options: list[DecisionOption] | None = None


class FilterAction(BaseModel):
    key: str
    label: str


class FilterRequester(BaseModel):
    type: str
    id: int | None = None
    name: str


class ApprovalFilterOptions(BaseModel):
    """What this brand's inbox can be narrowed by: only values its own requests
    carry (2026-10-03)."""

    actions: list[FilterAction]
    requesters: list[FilterRequester]


class DecisionRequest(BaseModel):
    reason: str | None = None
    #: ADR-141 §4's "pick-one for options": N options are ONE request, and the
    #: index says which the human chose. Absent means yes/no.
    choice_index: int | None = None


class DecisionResult(BaseModel):
    ok: bool
    message: str
    status: str


class ProcessExpiredResult(BaseModel):
    """What retiring the overdue requests did. Bookkeeping only — approving
    refuses an expired request whatever this has or has not done."""

    expired: int
    pending_action_ids: list[int] = []
