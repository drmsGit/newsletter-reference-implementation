-- migrate_0002_exclusion_reason.sql
--
-- ADR-163 point 8 — record WHY a recipient was excluded, not merely that they
-- were.
--
-- Adds `delivery_executions.exclusion_reason`, populated only when
-- `status = 'excluded'`. That status is new too, but statuses are free text in
-- this schema, so only the column needs DDL.
--
-- PURELY ADDITIVE. It drops nothing and rewrites nothing. Existing rows get
-- NULL, which is correct: they were never evaluated by the exclusion stack.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0002_exclusion_reason.sql

BEGIN;

ALTER TABLE delivery_executions
    ADD COLUMN IF NOT EXISTS exclusion_reason VARCHAR(255);

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0002 verification ---'

SELECT
    (SELECT count(*) FROM information_schema.columns
       WHERE table_name = 'delivery_executions'
         AND column_name = 'exclusion_reason')          AS exclusion_reason_col,
    (SELECT count(*) FROM delivery_executions)          AS executions,
    (SELECT count(*) FROM delivery_executions
       WHERE status = 'excluded')                       AS already_excluded;

\echo 'exclusion_reason_col must be 1. already_excluded is 0 until a send runs.'
\echo ''
