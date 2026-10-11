-- migrate_0048_consent_execution.sql
--
-- task-58, [[ADR-196 — Reporting Is the Campaign's Results Section; Analysis Belongs in the Adopter's Tools]]:
-- a consent event records the delivery it came through — a send's
-- unsubscribe link, or a provider bounce or complaint — so unsubscribes can
-- be counted per send. Events written before this have none and are not
-- counted; nothing is guessed for them. SET NULL on delete: a delivery row
-- going away must never take a consent record with it.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE consent_events ADD COLUMN IF NOT EXISTS delivery_execution_id INTEGER
    REFERENCES delivery_executions(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_consent_events_delivery_execution_id
    ON consent_events (delivery_execution_id) WHERE delivery_execution_id IS NOT NULL;

COMMIT;
