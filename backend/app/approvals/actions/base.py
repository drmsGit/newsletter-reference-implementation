"""What an approvable action declares, and what it hands back.

**Deliberately weaker than [[ADR-141]] §1's task contract.** That one requires a
task to declare *which record it writes*. This one requires only *what running
it does*, and `subject_type` may be `None` — which is the whole of ADR-142 §10's
awkward case ("AI can propose configuration changes … the landing place is
settings, not a record") absorbed without a special path. A settings action
declares no subject, describes itself in rows, and writes through the settings
service. Nothing in the spine changes to accommodate it.

**A separate registry, not a field on `TaskMeta`.** An AI task and an approvable
action are orthogonal: running a task is never the approvable act, applying its
output is. Fusing them would force every approvable action — a machine send, a
settings change — to carry a prompt and a token ceiling it has no use for.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ApprovableAction:
    """The declaration a module in `app/approvals/actions/` exposes as `META`."""

    #: Permanent identifier, e.g. "send.fire_send_instance". A history row has
    #: to resolve its action a year after the fact, so renaming one orphans
    #: history — the same rule ADR numbers and `TaskMeta.key` carry.
    key: str
    label: str

    #: A permission key from `app.auth.permissions`, checked against the person
    #: **approving**.
    #:
    #: **Declared rather than derived from the requesting route**, because what
    #: the requester needed and what approving needs are different questions
    #: about different principals. They coincide for a machine send — a human
    #: who may fire a send may approve one — and diverge for an AI suggestion,
    #: where requesting costs `ai.run` and approving writes the variant, which
    #: is `campaigns.manage`. That divergence is why this is a field and not an
    #: inference.
    approve_permission: str

    #: ADR-142 §4: "Pending actions expire. A held 'send the morning campaign'
    #: is worthless three days later." Every action supplies one, so the column
    #: can be NOT NULL and a forgetful module cannot mint an immortal request.
    default_ttl_seconds: int

    #: What the request is about — "send_instance", "variant", "ai_run" — or
    #: None for an action with no record behind it (ADR-142 §10).
    subject_type: str | None = None

    description: str = ""


@dataclass
class ActionDescription:
    """What the reviewer is shown. Produced **live**, on every render.

    Separate from `pending_actions.summary`, which is frozen at request time,
    and the split is the point: the frozen line keeps an expired row readable
    after its subject is deleted, while this call shows the approver what is
    true *now* — "this audience resolves to 1,310 recipients today, not the
    1,240 it did when the request was made". A person approving a send needs the
    second; a person reading history needs the first.
    """

    summary: str
    #: Label/value pairs. Plain strings — this is a review panel, not a form.
    rows: list[tuple[str, str]] = field(default_factory=list)
    #: Anything that should give the approver pause. Rendered, never enforced:
    #: a warning that blocks is a guard wearing the wrong clothes.
    warnings: list[str] = field(default_factory=list)
    #: A deep link into the record, when there is one.
    link: str | None = None
    #: ADR-141 §4's "pick-one for options". N options are ONE pending action,
    #: never N of them — three proposed subject lines are a single decision.
    options: list[dict] | None = None


@dataclass
class ActionResult:
    ok: bool
    message: str | None = None
    #: The action's own audit verb, e.g. "send.fired". Recorded with the
    #: **approver** as actor — which is where ADR-140 §5's "approver-if-gated"
    #: actually lands: as the actor of the domain event, not as a column on a
    #: domain table.
    audit_action: str | None = None
    audit_detail: dict | None = None
