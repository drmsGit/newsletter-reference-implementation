-- migrate_0017_pending_actions.sql
--
-- [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4: "the
-- platform holds the pending action; approving executes it." A flow calls an
-- action, receives "pending approval", and **finishes** — it does not park a
-- long-running execution waiting for a human.
--
-- This is the FIRST SLICE. It builds the spine and wires it to nothing; the
-- machine send becomes its first consumer in a later commit. What is
-- deliberately absent, named so nobody assumes otherwise:
--
--   * notifications of any kind (§4 constrains their form, not their existence,
--     and they would depend on the unbuilt system-mail channel);
--   * standing approvals — "an automated cycle is approved once, at setup" is a
--     grant with a scope and a revocation, not a status on this row;
--   * the settings action of §10. The contract admits it via a null
--     `subject_type`; no module ships.
--
-- PURELY ADDITIVE. One new table, no column touched anywhere else.
--
-- NO FOREIGN KEYS, deliberately — the same asymmetry `audit_events` has, one
-- level down. §4 requires that "approved, rejected *and* expired requests stay
-- inspectable", and a row referencing a send instance that was later deleted
-- must still read. A polymorphic subject makes an FK impossible regardless.

CREATE TABLE IF NOT EXISTS pending_actions (
    id                SERIAL PRIMARY KEY,

    -- The registry key of the action to run. Permanent, like `TaskMeta.key` and
    -- `ai_runs.task_key`: a history row must still resolve its action a year
    -- later, so renaming one orphans history and is forbidden for that reason.
    action_key        VARCHAR(100) NOT NULL,

    -- Everything `execute(db, payload)` needs, and nothing else. Internal
    -- identifiers and non-personal metadata only (ADR-153 point 5 binds what may
    -- be written about an action). NOT NULL: an action with no arguments passes
    -- `{}`, and "no payload at all" is a bug rather than a state.
    payload           JSON NOT NULL,

    -- **Frozen at request time**, and that is the point. `describe()` is re-run
    -- live on the review screen so the approver sees current reality; this line
    -- keeps an expired row readable after the thing it refers to is gone. One
    -- stored blob cannot do both jobs, which is why `describe` is a function and
    -- this is a column.
    summary           VARCHAR(500) NOT NULL,

    -- Reuses audit's actor vocabulary verbatim ('user' | 'integration' |
    -- 'system'), because one vocabulary is the whole of ADR-166 point 1's
    -- "not a parallel authorization system" at the data layer.
    requested_by_type VARCHAR(50) NOT NULL,
    -- Nullable for the reason `audit_events.actor_id` is: with access control
    -- switched off there is genuinely no actor, and inventing one is worse.
    requested_by_id   INTEGER,

    -- Polymorphic, allowed to dangle. Both nullable — and that nullability IS
    -- the ADR-142 §10 answer: a proposed settings change has no record to point
    -- at, and the contract accommodates it by requiring a subject of nothing.
    subject_type      VARCHAR(50),
    subject_id        INTEGER,

    -- Nullable in the schema for the subject-less case; required by the service
    -- whenever the approving permission is brand-scoped, because the inbox is
    -- per working brand and a null brand on a brand-scoped action would be
    -- invisible to everyone.
    brand_id          INTEGER,

    -- 'pending' | 'approved' | 'rejected' | 'expired' | 'failed'.
    -- `failed` is separate from `rejected` because "a human said no" and "the
    -- execution blew up" are different facts, and merging them makes the
    -- history lie about which one happened.
    status            VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- NOT NULL. §4: "Pending actions expire. A held 'send the morning campaign'
    -- is worthless three days later." A nullable TTL means the first action
    -- module that forgets one creates an immortal held send.
    expires_at        TIMESTAMPTZ NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- ADR-140 §5's "approver-if-gated", as columns. All three stay NULL for an
    -- expired row: nobody decided, and naming someone would be the same
    -- dishonesty `record()` refuses when it writes a null actor.
    decided_at        TIMESTAMPTZ,
    decided_by_type   VARCHAR(50),
    decided_by_id     INTEGER,

    -- ADR-141 §4: the component "shows the output(s) + reason".
    decision_reason   VARCHAR(1000),

    -- Set only alongside status='failed'. Deliberately not merged into
    -- decision_reason — one is typed by a human, the other is an exception.
    execution_error   VARCHAR(1000)
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_pending_actions_status') THEN
        ALTER TABLE pending_actions ADD CONSTRAINT ck_pending_actions_status
            CHECK (status IN ('pending','approved','rejected','expired','failed'));
    END IF;

    -- Decided-ness is one fact stored in two columns, so the database keeps them
    -- agreeing rather than trusting every future call site to.
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_pending_actions_decided') THEN
        ALTER TABLE pending_actions ADD CONSTRAINT ck_pending_actions_decided
            CHECK ((status = 'pending') = (decided_at IS NULL));
    END IF;
END $$;

-- One open request per thing, the same idiom as
-- `ux_content_overrides_one_active_per_module`. An orchestrator that retries a
-- refused call must not produce two held sends for send instance 12. It
-- degrades correctly for the subject-less case: Postgres treats NULLs as
-- distinct, so settings-shaped actions never collide with each other.
CREATE UNIQUE INDEX IF NOT EXISTS ux_pending_actions_one_open_per_subject
    ON pending_actions (action_key, subject_type, subject_id)
    WHERE status = 'pending';

-- The inbox query: one brand, one status, newest first.
CREATE INDEX IF NOT EXISTS ix_pending_actions_inbox
    ON pending_actions (brand_id, status, created_at);
-- The expiry sweep.
CREATE INDEX IF NOT EXISTS ix_pending_actions_due
    ON pending_actions (status, expires_at);
-- "What has been asked about this send instance?"
CREATE INDEX IF NOT EXISTS ix_pending_actions_subject
    ON pending_actions (subject_type, subject_id);

-- Single-column indexes matching every `index=True` on the model, so the two
-- creation paths — this file and `Base.metadata.create_all` — do not disagree
-- about the schema (the rule migrate_0009 states).
CREATE INDEX IF NOT EXISTS ix_pending_actions_action_key
    ON pending_actions (action_key);
CREATE INDEX IF NOT EXISTS ix_pending_actions_status
    ON pending_actions (status);
CREATE INDEX IF NOT EXISTS ix_pending_actions_brand_id
    ON pending_actions (brand_id);
