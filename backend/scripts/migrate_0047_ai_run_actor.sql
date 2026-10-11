-- migrate_0047_ai_run_actor.sql
--
-- task-345, [[ADR-144 — AI Data and Model Governance]] addenda of 2026-10-09
-- and 2026-10-11: every AI run records who started it — "user",
-- "integration" or "system" (a sweep, no id). Runs recorded before this have
-- none and are shown as "not recorded"; nothing is guessed for them.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS actor_type VARCHAR(20);
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS actor_id INTEGER;

COMMIT;
