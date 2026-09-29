-- migrate_0022_pending_action_executing.sql
--
-- [[ADR-142 — Autonomous Workflows and the Automation Boundary]], addendum
-- 2026-09-29: a held action is claimed by STATE, not by lock (task-4, task-13).
--
-- Approving used to take `SELECT … FOR UPDATE` on the row and hold it across
-- the action — but the action runs on the same session, and
-- `send_send_instance` commits inside it. That commit released the lock while
-- the row still read 'pending', so two approvers could both execute. Approval
-- now moves the row 'pending' → 'executing', committed, BEFORE the action
-- runs, and only the caller whose move succeeded finalises it.
--
-- Two changes, both to what 0017 built:
--
--   1. `ck_pending_actions_status` admits 'executing'.
--   2. `ux_pending_actions_one_open_per_subject` covers 'pending' AND
--      'executing'. An executing request still occupies its subject: nobody
--      may hold a second request for a send whose approved action is running.
--
-- `ck_pending_actions_decided` is untouched. `decided_at` is set at the claim,
-- because that is when the person decided, so only 'pending' is undecided —
-- exactly what that constraint already says.
--
-- SAFE ON EXISTING DATA. No row can be 'executing' before this migration, so
-- widening the index cannot find a duplicate that the old one allowed.
--
-- The first migration applied through ADR-181's runner:
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE pending_actions DROP CONSTRAINT IF EXISTS ck_pending_actions_status;
ALTER TABLE pending_actions ADD CONSTRAINT ck_pending_actions_status
    CHECK (status IN ('pending','executing','approved','rejected','expired','failed'));

DROP INDEX IF EXISTS ux_pending_actions_one_open_per_subject;
CREATE UNIQUE INDEX ux_pending_actions_one_open_per_subject
    ON pending_actions (action_key, subject_type, subject_id)
    WHERE status IN ('pending', 'executing');

COMMIT;
