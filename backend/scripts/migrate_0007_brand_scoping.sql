-- migrate_0007_brand_scoping.sql
--
-- [[ADR-150 — Tenancy and Access Model]] point 2, accepted 2026-09-14:
-- **multi-brand is the ordinary case**, not a state a company escalates into.
-- The first pilot customer runs around ten brands and adds several a year.
--
-- Until now `role_assignments.brand_id` was the ONLY brand foreign key in the
-- database. `has_permission(db, user, permission, brand_id=None)` already
-- filtered on a brand and no caller ever passed one — because nothing else
-- belonged to a brand, so a grant saying "Manager on brand 2" had nothing to
-- be checked against. This script gives brand something to mean.
--
-- Four tables gain the scope, one gains the working context:
--   content_records    NOT NULL  — one brand per record (sharing was rejected
--                                  2026-09-15: the same copy under two brands
--                                  needs different URLs and domains, so 1:1
--                                  reuse is not realistic; duplication is the
--                                  escape hatch)
--   campaigns          NOT NULL  — composed for one brand
--   audience_groups    NOT NULL  — ownership, not membership (see below)
--   send_instances     NOT NULL  — the sending brand (ADR-150 point 9)
--   auth_sessions      NULLABLE  — which brand this session is working in
--
-- `recipients`, `signal_contributions`, `categories` and `app_config` get
-- NOTHING: ADR-150 points 9, 8 and 2 rule each out explicitly. Consent is
-- deliberately NOT touched here — brand on the consent grid is Phase 2 and
-- needs an addendum to [[ADR-163]] first, because it changes a compliance path.
--
-- ALSO SWAPS AN INDEX. `ux_audience_groups_name_lower` is globally unique on
-- lower(name), so two brands could not both own a group called "VIPs". It is
-- replaced by `ux_audience_groups_brand_name_lower` on (brand_id, lower(name)).
-- The old index is dropped only AFTER the new one exists.
--
-- ---------------------------------------------------------------------------
-- On the backfill, and why it does not break this repo's own rule
-- ---------------------------------------------------------------------------
-- migrate_0003 refused to backfill counts ("a computed number here would be
-- indistinguishable from a recorded one") and migrate_0001a chose
-- source='migration' over source='crm' because "asserting the CRM said this
-- would be inventing evidence". Both refusals stand.
--
-- This backfill is a different kind. There is exactly ONE brand in the
-- database, so assigning existing rows to it is not a guess standing in for
-- unknowable history — it is the only value those rows could ever have had.
-- The script asserts that precondition rather than assuming it: if a second
-- brand already exists, it REFUSES, because then the answer really would be
-- unknowable and choosing one is a judgement this script must not make.
--
-- CHECKED ON THE DEV DATABASE 2026-09-15, before writing:
--   brands 1 · content_records 144 · campaigns 7 · audience_groups 12
--   send_instances 7 · auth_sessions 37
--
-- No migration in this repository had previously added a NOT NULL FOREIGN KEY
-- to a populated table — every earlier NOT NULL was a scalar with a
-- semantically empty default ('email', 0, TRUE). So this is done in three
-- steps: add nullable, backfill, then SET NOT NULL guarded on zero remaining
-- nulls, raising rather than forcing.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0007_brand_scoping.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Preconditions — guard rather than trust
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    brand_count INTEGER;
    has_column  BOOLEAN;
    unassigned  INTEGER;
BEGIN
    SELECT count(*) INTO brand_count FROM brands;

    IF brand_count = 0 THEN
        RAISE EXCEPTION
            'No brand exists. Start the app once so bootstrap_auth() seeds the '
            'default brand, then re-run this script.';
    END IF;

    IF brand_count > 1 THEN
        -- Several brands is only a problem while rows are still unassigned.
        -- Once the backfill has run, re-running is fine.
        --
        -- The reference to content_records.brand_id below MUST go through
        -- EXECUTE. Postgres resolves column references at PARSE time, so a
        -- plain `NOT EXISTS (SELECT 1 FROM content_records WHERE brand_id IS
        -- NULL)` guarded by an information_schema check fails with
        -- `column "brand_id" does not exist` on a database where the column is
        -- not there yet — the AND never gets the chance to short-circuit. That
        -- is the same trap migrate_0001a documents twice, and it cost this
        -- script its own error message once before being fixed: the operator
        -- saw a parse error instead of the sentence explaining what to do.
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'content_records' AND column_name = 'brand_id'
        ) INTO has_column;

        IF has_column THEN
            EXECUTE 'SELECT count(*) FROM content_records WHERE brand_id IS NULL'
               INTO unassigned;
        ELSE
            unassigned := -1;   -- no column yet, so nothing can be assigned
        END IF;

        IF has_column AND unassigned = 0 THEN
            RAISE NOTICE 'Several brands exist and the backfill has already run — continuing.';
        ELSE
            RAISE EXCEPTION
                '% brands exist and rows are still unassigned. This script can only '
                'backfill when there is exactly one brand, because with several the '
                'correct brand per row is unknowable and guessing it would invent '
                'evidence. Assign them by hand.', brand_count;
        END IF;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. Expand — add the columns, nullable for now
-- ---------------------------------------------------------------------------

ALTER TABLE content_records ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES brands(id);
ALTER TABLE campaigns       ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES brands(id);
ALTER TABLE audience_groups ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES brands(id);
ALTER TABLE send_instances  ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES brands(id);

-- The working context. Stays nullable for the life of the column: a session
-- that predates the switcher, or one whose user holds no grant, has no working
-- context, and the resolver falls back rather than the column lying.
ALTER TABLE auth_sessions   ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES brands(id);

CREATE INDEX IF NOT EXISTS ix_content_records_brand_id ON content_records (brand_id);
CREATE INDEX IF NOT EXISTS ix_campaigns_brand_id       ON campaigns (brand_id);
CREATE INDEX IF NOT EXISTS ix_audience_groups_brand_id ON audience_groups (brand_id);
CREATE INDEX IF NOT EXISTS ix_send_instances_brand_id  ON send_instances (brand_id);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_brand_id   ON auth_sessions (brand_id);

-- ---------------------------------------------------------------------------
-- 2. Backfill — the only brand there is
-- ---------------------------------------------------------------------------

UPDATE content_records SET brand_id = (SELECT id FROM brands ORDER BY id LIMIT 1) WHERE brand_id IS NULL;
UPDATE campaigns       SET brand_id = (SELECT id FROM brands ORDER BY id LIMIT 1) WHERE brand_id IS NULL;
UPDATE audience_groups SET brand_id = (SELECT id FROM brands ORDER BY id LIMIT 1) WHERE brand_id IS NULL;
UPDATE send_instances  SET brand_id = (SELECT id FROM brands ORDER BY id LIMIT 1) WHERE brand_id IS NULL;

-- Deliberately NOT backfilled: auth_sessions.brand_id. A live session picks up
-- its working context on the next request from the user's own grants, which is
-- the honest source. Writing a brand into somebody's existing session would be
-- asserting a choice they never made.

-- ---------------------------------------------------------------------------
-- 3. Contract — refuse to proceed if anything is still unassigned
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    stragglers INTEGER;
BEGIN
    SELECT (SELECT count(*) FROM content_records WHERE brand_id IS NULL)
         + (SELECT count(*) FROM campaigns       WHERE brand_id IS NULL)
         + (SELECT count(*) FROM audience_groups WHERE brand_id IS NULL)
         + (SELECT count(*) FROM send_instances  WHERE brand_id IS NULL)
      INTO stragglers;

    IF stragglers > 0 THEN
        RAISE EXCEPTION
            '% rows still have no brand after the backfill. Not setting NOT NULL — '
            'forcing it would either fail loudly here or, worse, succeed against a '
            'value somebody guessed.', stragglers;
    END IF;
END $$;

ALTER TABLE content_records ALTER COLUMN brand_id SET NOT NULL;
ALTER TABLE campaigns       ALTER COLUMN brand_id SET NOT NULL;
ALTER TABLE audience_groups ALTER COLUMN brand_id SET NOT NULL;
ALTER TABLE send_instances  ALTER COLUMN brand_id SET NOT NULL;

-- ---------------------------------------------------------------------------
-- 4. The audience unique index, rescoped to the brand
-- ---------------------------------------------------------------------------

CREATE UNIQUE INDEX IF NOT EXISTS ux_audience_groups_brand_name_lower
    ON audience_groups (brand_id, lower(name));

-- Dropped only now, after its replacement exists, so there is no window in
-- which duplicate names could be created.
DROP INDEX IF EXISTS ux_audience_groups_name_lower;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0007 verification ---'

SELECT
    (SELECT count(*) FROM information_schema.columns
      WHERE column_name = 'brand_id'
        AND table_name IN ('content_records','campaigns','audience_groups',
                           'send_instances','auth_sessions','role_assignments')) AS brand_columns,
    (SELECT count(*) FROM content_records WHERE brand_id IS NULL)                AS content_unassigned,
    (SELECT count(*) FROM campaigns       WHERE brand_id IS NULL)                AS campaigns_unassigned,
    (SELECT count(*) FROM audience_groups WHERE brand_id IS NULL)                AS audiences_unassigned,
    (SELECT count(*) FROM send_instances  WHERE brand_id IS NULL)                AS sends_unassigned,
    (SELECT count(*) FROM pg_indexes
      WHERE indexname = 'ux_audience_groups_brand_name_lower')                   AS new_index,
    (SELECT count(*) FROM pg_indexes
      WHERE indexname = 'ux_audience_groups_name_lower')                         AS old_index;

\echo 'brand_columns must be 6 (the four new, the session context, and the'
\echo 'role_assignments column that already existed).'
\echo 'All four *_unassigned must be 0 — they are NOT NULL now, so a non-zero'
\echo 'value here would mean this script did not run.'
\echo 'new_index must be 1 and old_index 0.'
\echo ''

SELECT b.name AS brand,
       (SELECT count(*) FROM content_records WHERE brand_id = b.id) AS content,
       (SELECT count(*) FROM campaigns       WHERE brand_id = b.id) AS campaigns,
       (SELECT count(*) FROM audience_groups WHERE brand_id = b.id) AS audiences,
       (SELECT count(*) FROM send_instances  WHERE brand_id = b.id) AS sends
  FROM brands b ORDER BY b.id;

\echo 'On a first run against the dev database this is one row reading'
\echo '144 / 7 / 12 / 7 — every existing row on the single default brand.'
\echo ''
