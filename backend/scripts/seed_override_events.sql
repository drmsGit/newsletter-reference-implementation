-- Seed data for override_events table
-- Safe to re-run: deletes existing override_events before inserting.
-- Requires: module_instances (1,2), decision_slots (1), content_records (1,2,3), send_instances (1) to exist.

BEGIN;

DELETE FROM override_events;

-- Override 1: manager swapped content on a decision slot
-- System picked content 1 (Mallorca Beach Walk), manager chose content 2 (Rome City Weekend)
INSERT INTO override_events (
    override_type,
    module_instance_id,
    decision_slot_id,
    send_instance_id,
    system_content_record_id,
    override_content_record_id,
    overridden_by,
    reason,
    outcome_delta,
    created_at
) VALUES (
    'content',
    2,
    1,
    1,
    1,
    2,
    'manager@example.com',
    'City weekend fits the spring campaign better',
    NULL,
    NOW()
);

-- Override 2: silent override, no reason given, outcome already recorded
INSERT INTO override_events (
    override_type,
    module_instance_id,
    decision_slot_id,
    send_instance_id,
    system_content_record_id,
    override_content_record_id,
    overridden_by,
    reason,
    outcome_delta,
    created_at
) VALUES (
    'content',
    1,
    NULL,
    1,
    3,
    1,
    'manager@example.com',
    NULL,
    '{"system_open_rate": 0.21, "override_open_rate": 0.18, "system_click_rate": 0.04, "override_click_rate": 0.03}',
    NOW() - INTERVAL '7 days'
);

COMMIT;
