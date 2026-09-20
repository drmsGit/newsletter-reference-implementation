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
    expires_at: datetime
    decided_at: datetime | None


class DescriptionRow(BaseModel):
    label: str
    value: str


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


class DecisionRequest(BaseModel):
    reason: str | None = None
    #: ADR-141 §4's "pick-one for options": N options are ONE request, and the
    #: index says which the human chose. Absent means yes/no.
    choice_index: int | None = None


class DecisionResult(BaseModel):
    ok: bool
    message: str
    status: str
