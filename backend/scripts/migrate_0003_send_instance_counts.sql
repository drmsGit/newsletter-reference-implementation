-- migrate_0003_send_instance_counts.sql
--
-- P1 (code review 2026-08-07, P1-03) — a send instance reported `sent` even
-- when every delivery failed, because the status was set unconditionally after
-- the loop rather than derived from the child executions.
--
-- Adds the three counts the parent status is now derived from.
-- `excluded_count` is separate from `failed_count` by design: an excluded
-- recipient is the ADR-163 point 7 exclusion stack working, not a delivery
-- problem, and folding them together would recreate the lie this fixes.
--
-- PURELY ADDITIVE. Existing rows get 0 for all three, which is honest — their
-- counts were never recorded and cannot be reconstructed for sends whose
-- executions have since been pruned. Do not backfill: a computed number here
-- would be indistinguishable from a recorded one.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0003_send_instance_counts.sql

BEGIN;

ALTER TABLE send_instances
    ADD COLUMN IF NOT EXISTS sent_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE send_instances
    ADD COLUMN IF NOT EXISTS failed_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE send_instances
    ADD COLUMN IF NOT EXISTS excluded_count INTEGER NOT NULL DEFAULT 0;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0003 verification ---'

SELECT
    (SELECT count(*) FROM information_schema.columns
       WHERE table_name = 'send_instances'
         AND column_name IN ('sent_count', 'failed_count', 'excluded_count')) AS new_columns,
    (SELECT count(*) FROM send_instances)                                     AS send_instances,
    (SELECT count(*) FROM send_instances WHERE status = 'sent')               AS status_sent;

\echo 'new_columns must be 3. Existing rows keep 0 counts — not backfilled, deliberately.'
\echo ''
