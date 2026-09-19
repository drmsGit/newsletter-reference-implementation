from sqlalchemy import (
    CheckConstraint, Column, DateTime, Integer, String, func, JSON,
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

STATUSES = (PENDING, APPROVED, REJECTED, EXPIRED, FAILED)
#: Everything that is no longer waiting on anybody.
DECIDED = (APPROVED, REJECTED, EXPIRED, FAILED)


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
    # what it references. Both nullable, and **that nullability is the ADR-142
    # §10 answer**: a proposed settings change has no record to point at, so the
    # contract accommodates it by requiring a subject of nothing rather than
    # inventing a fake one.
    subject_type = Column(String(50), nullable=True)
    subject_id = Column(Integer, nullable=True)

    # Required by the service whenever the approving permission is brand-scoped.
    # Nullable in the schema only for the subject-less case: a brand-scoped
    # action with no brand would be invisible in every brand's inbox, which is
    # the worst failure this table can have — something that looks accepted and
    # that nobody can see.
    brand_id = Column(Integer, nullable=True, index=True)

    status = Column(String(20), nullable=False, default=PENDING, index=True)

    # ADR-142 §4: "Pending actions expire." No default and no nullability — the
    # registry always supplies one, so a module that forgets cannot create an
    # immortal held send.
    expires_at = Column(DateTime(timezone=True), nullable=False)
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
            "status IN ('pending','approved','rejected','expired','failed')",
            name="ck_pending_actions_status",
        ),
        # Decided-ness is one fact held in two columns, so the database keeps
        # them agreeing rather than trusting every future call site to.
        CheckConstraint(
            "(status = 'pending') = (decided_at IS NULL)",
            name="ck_pending_actions_decided",
        ),
        # NOTE: the "one open request per subject" rule is a PARTIAL unique
        # index (`WHERE status = 'pending'`), which SQLAlchemy's
        # UniqueConstraint cannot express. It lives in
        # `scripts/migrate_0017_pending_actions.sql` only — so a database built
        # by `create_all` alone does NOT have it, and the service's own
        # duplicate check is what holds there. Both are tested separately,
        # because either one alone would make the other's test pass.
    )
