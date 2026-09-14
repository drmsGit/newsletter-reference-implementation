-- migrate_0006_content_unique_constraints.sql
--
-- Backlog bug (code-slimmer sweep 2026-08-21, Cluster 3 C1 + C5) — two
-- check-then-insert races with no database backstop. The identical race was
-- closed for audience members and recipient preferences on 2026-07-12;
-- content was missed.
--
-- (a) content_category_assignments (content_id, category_id) — a duplicate
--     assignment is merely wrong data.
-- (b) content_versions (content_record_id, version_number) — worse. ADR-128
--     makes a version the audit answer to "what exact content did this
--     recipient receive?", and two rows sharing a number make
--     resolve_renderable_content's `ORDER BY version_number DESC ... .first()`
--     pick one ARBITRARILY. The audit answer becomes a coin toss.
--
-- `create_all()` never alters an existing table, so declaring the constraints
-- on the models does nothing to a database that already exists. This script is
-- the actual change.
--
-- CHECKED BEFORE WRITING, on the dev database 2026-09-14 — both queries
-- returned zero rows against 315 assignments and 100 versions, so these
-- constraints cannot fail on existing data there. **Re-run both on any other
-- database before applying**, because a duplicate makes ADD CONSTRAINT abort
-- the transaction, and deciding which duplicate to keep is a judgement call
-- this script must not make for you:
--
--   SELECT content_id, category_id, count(*)
--     FROM content_category_assignments GROUP BY 1,2 HAVING count(*) > 1;
--   SELECT content_record_id, version_number, count(*)
--     FROM content_versions GROUP BY 1,2 HAVING count(*) > 1;
--
-- Idempotent: safe to run twice. ADD CONSTRAINT has no IF NOT EXISTS, so each
-- is guarded on pg_constraint instead.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0006_content_unique_constraints.sql

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'uq_content_category_assignments_content_category'
    ) THEN
        ALTER TABLE content_category_assignments
            ADD CONSTRAINT uq_content_category_assignments_content_category
            UNIQUE (content_id, category_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'uq_content_versions_record_version'
    ) THEN
        ALTER TABLE content_versions
            ADD CONSTRAINT uq_content_versions_record_version
            UNIQUE (content_record_id, version_number);
    END IF;
END $$;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0006 verification ---'

SELECT
    (SELECT count(*) FROM pg_constraint
      WHERE conname = 'uq_content_category_assignments_content_category') AS assignments_uq,
    (SELECT count(*) FROM pg_constraint
      WHERE conname = 'uq_content_versions_record_version')               AS versions_uq,
    (SELECT count(*) FROM content_category_assignments)                   AS assignments,
    (SELECT count(*) FROM content_versions)                               AS versions;

\echo 'Both _uq columns must be 1. Row counts are shown so a zero-duplicate'
\echo 'result above is not confused with an empty table.'
\echo ''
