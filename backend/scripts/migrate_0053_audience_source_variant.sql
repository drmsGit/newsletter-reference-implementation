-- migrate_0053_audience_source_variant.sql
--
-- [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]], addendum 2026-10-18:
-- a suggested audience is made per variant, its topics and its language.
--   * audience_groups.source_variant_id: the variant a suggested group was
--     made from, beside its source campaign, so Recalculate follows that
--     variant. NULL for a hand-made group and for a campaign-wide suggestion.
--     A deleted variant leaves the group standing, unlinked.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE audience_groups ADD COLUMN IF NOT EXISTS source_variant_id INTEGER
    REFERENCES variants(id) ON DELETE SET NULL;

COMMIT;
