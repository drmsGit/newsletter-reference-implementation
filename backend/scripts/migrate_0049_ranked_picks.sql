-- migrate_0049_ranked_picks.sql
--
-- task-109, [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
-- addendum of 2026-10-11: a slot shows up to N picks, so a resolution row is
-- one pick in a ranked set. `rank` is its place (1 = first); `pick_set` is
-- shared by the rows one execution wrote. Rows from before have no set and
-- count as a set of one, at rank 1.
--
-- "Show up to" becomes 1-5 and a push slot is always 1: values outside are
-- brought inside first, then held by a CHECK.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE decision_resolutions ADD COLUMN IF NOT EXISTS rank INTEGER NOT NULL DEFAULT 1;
ALTER TABLE decision_resolutions ADD COLUMN IF NOT EXISTS pick_set VARCHAR(32);
CREATE INDEX IF NOT EXISTS ix_decision_resolutions_pick_set
    ON decision_resolutions (pick_set) WHERE pick_set IS NOT NULL;

UPDATE decision_slots SET max_results = LEAST(GREATEST(max_results, 1), 5)
    WHERE max_results NOT BETWEEN 1 AND 5;
UPDATE decision_slots SET max_results = 1
    WHERE max_results <> 1
      AND variant_id IN (SELECT id FROM variants WHERE channel = 'push');

ALTER TABLE decision_slots DROP CONSTRAINT IF EXISTS ck_decision_slots_max_results;
ALTER TABLE decision_slots ADD CONSTRAINT ck_decision_slots_max_results
    CHECK (max_results BETWEEN 1 AND 5);

COMMIT;
