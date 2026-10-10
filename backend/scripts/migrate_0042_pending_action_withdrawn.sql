-- migrate_0042_pending_action_withdrawn.sql
--
-- task-331, [[ADR-142 — Autonomous Workflows and the Automation Boundary]]:
-- second addendum of 2026-10-09 and its 2026-10-10 paragraph. When a person
-- approves a held request whose requester is no longer allowed (switched off,
-- or no longer holding the action's request permission), nothing runs and the
-- request closes as 'withdrawn'. A seventh status rather than 'rejected' (a
-- person refused) or 'failed' (it ran and went wrong): nobody refused it and
-- nothing ran.
--
-- Only `ck_pending_actions_status` changes. 'withdrawn' is decided, so
-- `ck_pending_actions_decided` already holds for it (only 'pending' is
-- undecided), and it does not occupy its subject, so the one-open-request
-- index ('pending', 'executing') is untouched.
--
-- SAFE ON EXISTING DATA: it only widens the set of allowed values.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE pending_actions DROP CONSTRAINT IF EXISTS ck_pending_actions_status;
ALTER TABLE pending_actions ADD CONSTRAINT ck_pending_actions_status
    CHECK (status IN ('pending','executing','approved','rejected','expired','failed','withdrawn'));

COMMIT;
