from sqlalchemy import (
    CheckConstraint, Column, DateTime, Index, Integer, String, func, text, JSON,
)

from app.database import Base

# --- the lifecycle ---------------------------------------------------------
PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
#: The execution raised. **Separate from REJECTED on purpose**: "a human said
#: no" and "the run blew up" are different facts, and one status covering both
#: makes the history lie about which happened.
FAILED = "failed"
#: A person approved and the action is running — or ran, and the process died
#: before recording how it went (ADR-142 addendum 2026-09-29). The claim that
#: makes approval run-once: `approve` moves a row here, committed, BEFORE the
#: action executes, so an action that commits internally can no longer release
#: the guard. **A row left here by a crash stays here, deliberately.** Nobody
#: can know whether the action ran, and re-approving it is the double execution
#: this state exists to prevent.
EXECUTING = "executing"
#: A person tried to approve, and the requester was no longer allowed —
#: switched off, or no longer holding the action's `request_permission`
#: (task-331, ADR-142 second addendum of 2026-10-09). Nothing ran and nobody
#: refused it, which is why it is neither REJECTED nor FAILED.
WITHDRAWN = "withdrawn"

STATUSES = (PENDING, EXECUTING, APPROVED, REJECTED, EXPIRED, FAILED, WITHDRAWN)
#: Everything that is no longer waiting on a person. EXECUTING is here because
#: the person has decided; it is shown with the decided rows rather than in the
#: inbox, which must never offer an Approve button on something already running.
DECIDED = (EXECUTING, APPROVED, REJECTED, EXPIRED, FAILED, WITHDRAWN)
#: A request that still occupies its subject: nobody may hold a second request
#: for a thing whose first is waiting, or whose approved action is running.
OPEN = (PENDING, EXECUTING)


class PendingActionDB(Base):
    """An action the platform is holding until a human approves it.

    [[ADR-142]] §4: "the platform holds the pending action; approving executes
    it." The caller — an orchestrator, or a guard that refused a machine — makes
    its call, receives "pending approval", and **finishes**. Nothing parks a
    long-running execution waiting for a person, so this survives a restart of
    the thing that asked.

    **This is a domain record, not a log.** It is mutable, it has one lifecycle,
    and it answers *what is waiting on me and what happens if I say yes*.
    `audit_events` stays the evidence and answers *who* — ADR-153's own division
    applied one level down. The two are kept honest by a rule rather than a
    foreign key: **`status` here is a cache of the latest audit entry, never an
    independent fact.** If they disagree, audit wins. The test that enforces it
    deletes every row in this table and asserts the decision history is still
    reconstructable from `events_for_subject("pending_action", id)`.

    That rule is what "it extends the ADR-140 audit surface; it is not a second
    log" means in practice. A pending action mutates four times; four separate
    append-only entries record it, and none of them is ever updated.
    """

    __tablename__ = "pending_actions"

    id = Column(Integer, primary_key=True, index=True)

    # The registry key of the action to run. Permanent: a history row has to
    # resolve its action a year later, so renaming one orphans history — the
    # same constraint `TaskMeta.key` and `ai_runs.task_key` carry.
    action_key = Column(String(100), nullable=False, index=True)

    # Everything `execute(db, payload)` needs, and nothing else. Internal
    # identifiers and non-personal metadata only.
    #
    # **The payload lives here and never in an audit entry's `detail`.** ADR-153
    # point 5 binds what may be written into the log, and a payload is an open
    # dict whose shape an action author controls. Audit points at this row; this
    # row holds the arguments.
    payload = Column(JSON, nullable=False)

    # Frozen at request time. `describe()` is re-run live on the review screen so
    # the approver sees current reality ("this audience now resolves to 1,310,
    # not the 1,240 when it was requested"); this line is what keeps an expired
    # row readable after its subject is gone. One value cannot do both jobs,
    # which is exactly why `describe` is a function and this is a column.
    summary = Column(String(500), nullable=False)

    # audit's vocabulary, verbatim: "user" | "integration" | "system".
    requested_by_type = Column(String(50), nullable=False)
    requested_by_id = Column(Integer, nullable=True)

    # Polymorphic, no foreign key, allowed to dangle — an entry must outlive
    # what it references. Both nullable in the schema, and that nullability was
    # meant as the ADR-142 §10 answer: a proposed settings change has no record
    # to point at. **That accommodation is withdrawn (2026-09-29, task-15).**
    # A NULL subject is invisible to the one-open-request index below, so
    # `request_approval` refuses any request without both. §10 must decide what
    # identifies a settings proposal before one can be held; the columns stay
    # nullable so that decision does not also need a migration.
    subject_type = Column(String(50), nullable=True)
    subject_id = Column(Integer, nullable=True)
    # A part of the subject an action may declare (task-206; ADR-142 addendum
    # 2026-10-08): the channel, for a readiness mark, so each channel of a
    # record has its own open request. Empty — never NULL — for an action that
    # declares none, because a unique index never sees two NULLs as equal and
    # would drop the one-open-request rule for every such action (migration 0040).
    subject_scope = Column(String(64), nullable=False, default="", server_default="")

    # Required by the service whenever the approving permission is brand-scoped.
    # Nullable in the schema only for the subject-less case: a brand-scoped
    # action with no brand would be invisible in every brand's inbox, which is
    # the worst failure this table can have — something that looks accepted and
    # that nobody can see.
    brand_id = Column(Integer, nullable=True, index=True)

    status = Column(String(20), nullable=False, default=PENDING, index=True)

    # ADR-142 §4: "Pending actions expire" — those whose type declares a
    # deadline. Empty for an action type that declares none (§4's addendum of
    # 2026-09-24; task-210, migration 0039), and read as "never expires"
    # everywhere, never as "already expired". A module cannot get an empty one
    # by forgetting: `default_ttl_seconds` has no default.
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ADR-140 §5's "approver-if-gated". All three stay NULL on an expired row:
    # nobody decided it.
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decided_by_type = Column(String(50), nullable=True)
    decided_by_id = Column(Integer, nullable=True)
    decision_reason = Column(String(1000), nullable=True)

    # Set only with status=FAILED, and deliberately not folded into
    # `decision_reason`: one is typed by a person, the other is an exception.
    execution_error = Column(String(1000), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','executing','approved','rejected','expired','failed','withdrawn')",
            name="ck_pending_actions_status",
        ),
        # Decided-ness is one fact held in two columns, so the database keeps
        # them agreeing rather than trusting every future call site to.
        CheckConstraint(
            "(status = 'pending') = (decided_at IS NULL)",
            name="ck_pending_actions_decided",
        ),
        # One open request per thing. A PARTIAL unique index, because a decided
        # request must not block the next one — the same idiom as
        # `ux_content_overrides_one_active_per_module`. **It holds only because
        # every request names its subject:** Postgres treats NULLs as distinct
        # here, so a request with a NULL subject would escape it entirely, and
        # `request_approval` refuses one for that reason (task-15).
        #
        # **Declared here as well as in migration 0017, deliberately.** An
        # earlier version of this comment said the partial clause "cannot be
        # expressed" in the model and left it to the migration alone — which is
        # wrong (`Index(..., postgresql_where=...)` expresses it exactly), and
        # the cost of being wrong showed up the moment a database was built by
        # `create_all` instead: the constraint was simply absent there, so the
        # two creation paths disagreed about the schema and only one of them
        # enforced the rule. The migration stays for databases that already
        # exist; this is what every new one gets.
        Index(
            "ux_pending_actions_one_open_per_subject",
            "action_key", "subject_type", "subject_id", "subject_scope",
            unique=True,
            # Both open states (ADR-142 addendum 2026-09-29): an executing
            # request still occupies its subject.
            postgresql_where=text("status IN ('pending', 'executing')"),
        ),
        # Created by migration 0017 and, until 2026-09-29, declared nowhere
        # else — so every database built by `create_all`, the test database
        # included, lacked them (task-12). Same names as the migration.
        # The inbox query: one brand, one status, newest first.
        Index("ix_pending_actions_inbox", "brand_id", "status", "created_at"),
        # The expiry sweep.
        Index("ix_pending_actions_due", "status", "expires_at"),
        # "What has been asked about this send instance?"
        Index("ix_pending_actions_subject", "subject_type", "subject_id"),
    )
