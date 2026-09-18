-- migrate_0012_drop_variant_envelope_columns.sql
--
-- The CONTRACT half of [[ADR-162 — Channel Rendering and Artifacts]] point 1.
-- Migration 0011 created a `header` module for every email variant holding
-- envelope copy and left the columns in place as a read fallback. Nothing
-- reads them any more, so they go — and with them the last channel-shaped
-- thing on a channel-neutral table.
--
-- **Verified before running, not assumed.** On the dev database: 9 variants
-- carried column copy, all 9 had a header module, and every column value was
-- byte-identical to its module value. The guard below re-checks that at
-- migration time, because a deployment that skipped 0011 would otherwise lose
-- recipient-facing copy silently — and a DROP COLUMN cannot be undone by
-- re-running anything.
--
-- The guard uses DO/EXECUTE rather than a plain statement for the reason
-- migrate_0008 learned: Postgres resolves column names at PARSE time, so a
-- script that mentions `variants.subject` after it has been dropped fails on
-- the second run with "column does not exist" instead of being idempotent.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0012_drop_variant_envelope_columns.sql

BEGIN;

DO $$
DECLARE
    stranded integer;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'variants' AND column_name = 'subject'
    ) THEN
        EXECUTE $q$
            SELECT count(*) FROM variants v
             WHERE (v.subject IS NOT NULL OR v.preheader IS NOT NULL)
               AND NOT EXISTS (
                   SELECT 1 FROM module_instances m
                    WHERE m.variant_id = v.id AND m.module_type = 'header')
        $q$ INTO stranded;

        IF stranded > 0 THEN
            RAISE EXCEPTION
                'Refusing to drop: % variant(s) still hold envelope copy with no header module. Run migrate_0011 first.',
                stranded;
        END IF;
    END IF;
END $$;

ALTER TABLE variants DROP COLUMN IF EXISTS subject;
ALTER TABLE variants DROP COLUMN IF EXISTS preheader;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------
-- Expect neither column:
--
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name = 'variants' ORDER BY ordinal_position;
--
-- Expect the copy to still be there, in the modules:
--
--   SELECT v.id, m.position, m.module_data
--     FROM variants v JOIN module_instances m
--       ON m.variant_id = v.id AND m.module_type = 'header'
--    ORDER BY v.id;
