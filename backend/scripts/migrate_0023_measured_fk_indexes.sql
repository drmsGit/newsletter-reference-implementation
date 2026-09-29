-- migrate_0023_measured_fk_indexes.sql
--
-- The tail of 0018: of the unindexed foreign keys that migration left, the four
-- that grow per recipient or per event were measured one by one (task-11).
-- Two earn an index. Two do not, and are named so nobody adds them by rule.
--
-- MEASURED 2026-09-29 against synthetic volume in the test database, inside a
-- transaction that was rolled back. EXPLAIN (ANALYZE, BUFFERS), median of six
-- warm runs. Each row is the real query from the code, before and after:
--
--   engagement_events (delivery_execution_id)
--     insight/service.py list_events_for_delivery_execution, 100,000 events
--       2.235 ms / 738 buf  ->  0.005 ms / 4 buf
--     A scan over every event ever recorded, to return two.
--
--   decision_resolutions (decision_slot_id, recipient_id)       -- COMPOSITE
--     rendering/service.py, per recipient per send, 100,000 rows (20 x 5,000)
--       0.184 ms / 38 buf   ->  0.005 ms / 3 buf
--     providers/service.py click attribution (slot IN (...) AND recipient)
--       0.536 ms / 112 buf  ->  0.006 ms / 9 buf
--     Also serves the resolution dedup in decision/service.py, again once per
--     recipient per send. The existing slot index narrows to one slot and then
--     walks every recipient in it — linear per recipient, quadratic across a
--     send: roughly 18 ms per recipient at 500,000 recipients per slot.
--     `recipient_id` alone measured 0.034 ms: it scales too, but the composite
--     is the exact shape of all three hot queries.
--
-- **Measured and deliberately NOT indexed:**
--
--   signal_contributions (event_id)       0.042 ms -> 0.004 ms
--     The dedup check filters recipient AND category AND event, and the
--     existing `recipient_id` index already bounds it to one recipient's own
--     contributions. 38 microseconds, and the saving does not grow with the
--     table — only with one person's history.
--
--   content_category_assignments (category_id)   0.201 ms -> 0.029 ms, buffers unchanged
--     A structural table that stays small. The cost that matters is not the
--     scan but its multiplier: `top_score` does not depend on the recipient,
--     yet the send loop executes it once per recipient per slot. That is
--     logged as task-234; an index would hide it rather than fix it.
--
-- The other unindexed foreign keys are on structural tables that stay small,
-- as 0018 recorded, and were not measured. `delivery_executions.send_instance_id`
-- remains unindexed by 0018's own measurement (an unselective lookup).
--
-- PURELY ADDITIVE and safe to re-run. Not CONCURRENTLY, for 0018's reason:
-- these tables are small in every deployment that exists, and this directory
-- is applied inside a transaction.

CREATE INDEX IF NOT EXISTS ix_engagement_events_delivery_execution_id
    ON engagement_events (delivery_execution_id);

CREATE INDEX IF NOT EXISTS ix_decision_resolutions_slot_recipient
    ON decision_resolutions (decision_slot_id, recipient_id);
