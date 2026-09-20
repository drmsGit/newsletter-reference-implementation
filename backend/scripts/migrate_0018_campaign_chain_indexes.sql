-- migrate_0018_campaign_chain_indexes.sql
--
-- Three foreign keys on the campaign chain carry no index, and Postgres does
-- not create one for a `REFERENCES` clause. The columns are the parent links
-- every child lookup filters on:
--
--     decision_resolutions -> decision_slots -> variants -> campaigns
--
-- MEASURED 2026-09-20 rather than assumed, against synthetic volume in the
-- test database. Each row is one query, before and after:
--
--   decision_resolutions.decision_slot_id   3.45 ms / 801 buf  ->  0.080 ms / 12 buf
--   variants.campaign_id                    1.335 ms / 617 buf ->  0.016 ms / 3 buf
--   decision_slots.variant_id               1.554 ms / 849 buf ->  0.014 ms / 3 buf
--
-- `decision_resolutions` is the one that matters most: it grows at one row per
-- recipient per slot, which is the fastest-growing table in the schema, and the
-- scan is linear in its total size regardless of how few rows the query wants.
--
-- **A fourth candidate was measured and deliberately NOT indexed.**
-- `delivery_executions.send_instance_id` came out at 1.511 ms before and
-- 1.439 ms after, with identical buffers — because a send instance owns most
-- of the table's rows, so the lookup is unselective and a sequential scan is
-- the correct plan. Selectivity decides this, not foreign-key-ness. Twenty-two
-- further unindexed foreign keys remain, logged in `docs/backlog.md`, each
-- needing its own measurement before it earns an index.
--
-- PURELY ADDITIVE. No column, constraint or row is touched. Safe to re-run.
-- `IF NOT EXISTS` rather than a guard block, because a plain index needs no
-- DO block and the repeat case is "already there".
--
-- Not CONCURRENTLY: these tables are small in every deployment that exists
-- today, and CREATE INDEX CONCURRENTLY cannot run inside a transaction, which
-- is how the rest of this directory is applied. A deployment large enough to
-- care should build them concurrently by hand instead.

CREATE INDEX IF NOT EXISTS ix_variants_campaign_id
    ON variants (campaign_id);

CREATE INDEX IF NOT EXISTS ix_decision_slots_variant_id
    ON decision_slots (variant_id);

CREATE INDEX IF NOT EXISTS ix_decision_resolutions_decision_slot_id
    ON decision_resolutions (decision_slot_id);
