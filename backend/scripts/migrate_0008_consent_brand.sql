-- migrate_0008_consent_brand.sql
--
-- [[ADR-163 — Per-Channel Consent and Addressability]], addendum 2026-09-15:
-- **consent carries a brand**. The cell becomes
-- `(recipient, brand, channel, purpose)`, latest row still wins.
--
-- WHY THIS IS THE COMPLIANCE FIX, not a schema tidy-up. ADR-150's brand
-- columns landed on 2026-09-15 (migrate_0007) but consent did not, so the
-- authoring side was scoped and the send side was not: a campaign belonging to
-- brand B still reached **every consenting recipient**, because
-- `is_consenting_filter()` had no brand in it. Measured on this database
-- before writing: 41 recipients, and all 41 passed the gate regardless of
-- which brand asked.
--
-- Consent is to a SENDER. Opting in to brand A says nothing about brand B, so
-- a newly created brand starts with **zero reachable recipients** until
-- consent is captured for it. That is correct and it is the point, and it will
-- still surprise someone.
--
-- ---------------------------------------------------------------------------
-- The guard, and why it is NOT migrate_0007's
-- ---------------------------------------------------------------------------
-- migrate_0007 refused when more than one brand existed with rows unassigned,
-- because with several brands the correct brand per row is unknowable and
-- guessing it invents evidence. **That guard would refuse here**: a second
-- brand now exists.
--
-- A stronger argument is available, and it is a fact rather than a count.
-- Every existing consent row was written when the default brand was the only
-- brand that existed, which is provable from the timestamps:
--
--   newest consent_events row   2026-07-27 16:19:30+00
--   oldest non-default brand    2026-09-15 19:02:50+00
--
-- Seven weeks apart. So this script asserts what migrate_0003 refused to
-- assert — but the difference is the whole point of that refusal. 0003 would
-- not backfill counts "because a computed number here would be
-- indistinguishable from a recorded one". Here the value is not computed: at
-- the moment each row was written there was exactly one brand it could
-- possibly refer to, and the script REFUSES if that stops being true.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0008_consent_brand.sql

-- **Known limit of the guard below, recorded 2026-09-19 (interview review,
-- Brand Boundary Q8).** The precondition reads `min(created_at) FROM brands
-- WHERE id <> default_brand_id`, so it can only see brands that STILL EXIST.
-- A brand that was created and deleted before it captured consent leaves no
-- row, so consent written while it existed passes the check and is assigned
-- to the default brand silently.
--
-- Sound for this database and for the common single-brand install; not sound
-- in general. Written here rather than only in the review file because this
-- script ships in the repository, an adopter could run it, and the column it
-- backfills decides the record that answers a UWG §7 complaint.

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Preconditions — assert the timestamp fact rather than assume it
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    default_brand_id INTEGER;
    newest_consent   TIMESTAMPTZ;
    oldest_other     TIMESTAMPTZ;
    unassignable     INTEGER;
    has_column       BOOLEAN;
BEGIN
    SELECT id INTO default_brand_id FROM brands WHERE key = 'default';
    IF default_brand_id IS NULL THEN
        RAISE EXCEPTION
            'No default brand exists. Start the app once so bootstrap_auth() '
            'seeds it, then re-run.';
    END IF;

    -- Parse-time column resolution: consent_events.brand_id may not exist yet,
    -- so anything referencing it goes through EXECUTE. migrate_0001a documents
    -- this trap twice and migrate_0007 was bitten by it — an information_schema
    -- guard in a WHERE clause does not save a statement that cannot parse.
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'consent_events' AND column_name = 'brand_id'
    ) INTO has_column;

    IF has_column THEN
        EXECUTE 'SELECT count(*) FROM consent_events WHERE brand_id IS NULL'
           INTO unassignable;
    ELSE
        unassignable := (SELECT count(*) FROM consent_events);
    END IF;

    IF unassignable > 0 THEN
        SELECT max(created_at) INTO newest_consent FROM consent_events;
        SELECT min(created_at) INTO oldest_other
          FROM brands WHERE id <> default_brand_id;

        -- With no other brand, every row trivially belongs to the default one.
        IF oldest_other IS NOT NULL AND newest_consent >= oldest_other THEN
            RAISE EXCEPTION
                'A consent row was written at %, after the brand created at % — '
                'so it is NOT provable that every unassigned row predates every '
                'non-default brand, and assigning them to the default brand would '
                'be asserting consent nobody gave. Assign them by hand. (This is '
                'the one thing this script will not decide for you: consent is the '
                'record that answers a UWG section 7 complaint.)',
                newest_consent, oldest_other;
        END IF;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. Expand
-- ---------------------------------------------------------------------------

ALTER TABLE consent_events ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES brands(id);
CREATE INDEX IF NOT EXISTS ix_consent_events_brand_id ON consent_events (brand_id);

-- ---------------------------------------------------------------------------
-- 2. Backfill — the only brand that existed when these rows were written
-- ---------------------------------------------------------------------------

UPDATE consent_events
   SET brand_id = (SELECT id FROM brands WHERE key = 'default')
 WHERE brand_id IS NULL;

-- ---------------------------------------------------------------------------
-- 3. Contract
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    stragglers INTEGER;
BEGIN
    EXECUTE 'SELECT count(*) FROM consent_events WHERE brand_id IS NULL' INTO stragglers;
    IF stragglers > 0 THEN
        RAISE EXCEPTION
            '% consent rows still have no brand after the backfill. Not setting '
            'NOT NULL.', stragglers;
    END IF;
END $$;

ALTER TABLE consent_events ALTER COLUMN brand_id SET NOT NULL;

-- ---------------------------------------------------------------------------
-- 4. The cell index, rebuilt around the wider cell
-- ---------------------------------------------------------------------------
-- The read is "latest row for this cell", so the index carries the ordering as
-- well as the lookup. The new one is created before the old is dropped, so
-- there is no window in which the hot read is unindexed.

CREATE INDEX IF NOT EXISTS ix_consent_events_cell_latest_brand
    ON consent_events (recipient_id, brand_id, channel, purpose, created_at);

DROP INDEX IF EXISTS ix_consent_events_cell_latest;

ALTER INDEX IF EXISTS ix_consent_events_cell_latest_brand
    RENAME TO ix_consent_events_cell_latest;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0008 verification ---'

SELECT
    (SELECT count(*) FROM information_schema.columns
      WHERE table_name = 'consent_events' AND column_name = 'brand_id')      AS brand_column,
    (SELECT count(*) FROM consent_events WHERE brand_id IS NULL)             AS unassigned,
    (SELECT count(*) FROM consent_events)                                    AS consent_rows,
    (SELECT count(*) FROM pg_indexes
      WHERE indexname = 'ix_consent_events_cell_latest')                     AS cell_index;

\echo 'brand_column must be 1, unassigned 0 (the column is NOT NULL, so anything'
\echo 'else means this did not run), cell_index 1.'
\echo ''

SELECT b.name AS brand, count(c.id) AS consent_rows
  FROM brands b LEFT JOIN consent_events c ON c.brand_id = b.id
 GROUP BY b.name ORDER BY b.name;

\echo 'On a first run every row sits on the default brand — the only brand that'
\echo 'existed when they were written. Any other brand reading 0 is CORRECT and'
\echo 'is the point: it has zero reachable recipients until consent is captured.'
\echo ''
