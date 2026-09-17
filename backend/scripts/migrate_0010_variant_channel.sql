-- migrate_0010_variant_channel.sql
--
-- [[ADR-160 — Channel Model and Composition]] point 4, accepted and until now
-- unbuilt: **channel is an attribute on the variant.**
--
-- Until this ran, the word "channel" appeared in exactly one column in the
-- whole database — `delivery_executions.channel`, defaulting to 'email' — and
-- that is a **denormalised copy written at plan time**, not the model's home
-- for it. `delivery/service.py` says so in a comment: channel and purpose
-- "fall to their column defaults (email/marketing) — the only ones that exist
-- today. When a variant carries a channel (ADR-160 …)". This is that.
--
-- Deliberately NOT in this migration, and named so nobody assumes otherwise:
--
--   * ADR-162 point 1 — `subject` and `preheader` moving off the variant into
--     a `header` email module. They are email-shaped fields on a table that
--     ADR-162 says must hold no channel fields at all. An email variant still
--     uses them; a push variant leaves them NULL. Accepted debt, recorded here
--     rather than discovered later.
--   * ADR-164 point 9 — `signal_contributions.channel`.
--
-- Backfill: every existing variant is email. That is true by construction —
-- email was the only thing the system could render or send before today.
--
-- The DEFAULT is added and then DROPPED on purpose. It exists to fill existing
-- rows in one statement; leaving it behind would mean a caller that forgets to
-- pass a channel silently creates an email variant, which is fail-open the
-- moment a second channel exists. The model declares no server default either,
-- so the two creation paths agree.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0010_variant_channel.sql

BEGIN;

ALTER TABLE variants ADD COLUMN IF NOT EXISTS channel VARCHAR(50);

-- Backfill before the NOT NULL, or the constraint refuses every existing row.
UPDATE variants SET channel = 'email' WHERE channel IS NULL;

ALTER TABLE variants ALTER COLUMN channel SET NOT NULL;

-- And drop it again: see the header. ALTER ... DROP DEFAULT is a no-op when no
-- default is set, so this stays safe on a second run.
ALTER TABLE variants ALTER COLUMN channel DROP DEFAULT;

-- Matches the model's `index=True`, so a table built by create_all() and one
-- built by this script are identical. Two creation paths that disagree about
-- the schema is the bug migrate_0005 added a redundant index to avoid.
CREATE INDEX IF NOT EXISTS ix_variants_channel ON variants (channel);

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------
-- Expect: channel | character varying | NO  (nullable = NO, no default)
--
--   SELECT column_name, data_type, is_nullable, column_default
--     FROM information_schema.columns
--    WHERE table_name = 'variants' AND column_name = 'channel';
--
-- Expect every row to be 'email', and no NULLs:
--
--   SELECT channel, count(*) FROM variants GROUP BY channel;
