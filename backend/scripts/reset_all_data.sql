-- Full database reset + seed
-- Truncates all tables and inserts a complete, end-to-end testable dataset.
-- Safe to re-run at any time.
--
-- After running this script the system is in a state where:
--   - 3 content records with versions and category scores
--   - 1 campaign with 2 variants (A: beach focus, B: city focus)
--   - Each variant has 3 module instances: hero, decision-slot card, CTA
--   - 1 decision slot per variant (recipient_top_score strategy)
--   - 3 recipients with distinct preferences (beach / city / nature)
--   - 1 send instance with delivery executions and engagement events
--   - 1 override event pending outcome + 1 with outcome already recorded

BEGIN;

-- CASCADE handles FK order automatically
TRUNCATE TABLE
    preference_update_logs,
    engagement_events,
    delivery_executions,
    override_events,
    decision_resolutions,
    recipient_preferences,
    snapshots,
    send_instances,
    content_category_assignments,
    content_versions,
    category_relations,
    module_instances,
    decision_slots,
    variants,
    categories,
    recipients,
    campaigns,
    content_records
RESTART IDENTITY CASCADE;

-- =========================================================
-- CONTENT
-- =========================================================

INSERT INTO content_records (title, body, status) VALUES
    ('Mallorca Beach Walk',    'Discover the hidden coves of Mallorca''s northwest coast — a 12km walk between Port de Sóller and Sa Calobra.', 'active'),
    ('Rome City Weekend',      'Three days in Rome without the tourist traps: neighbourhood trattorias, the Trastevere market, and a private tour of the Borghese Gallery.', 'active'),
    ('Tenerife Nature Escape', 'Teide at sunrise, laurel forest hikes in Anaga, and the star-gazing plateau of El Médano — Tenerife beyond the resorts.', 'active');

INSERT INTO content_versions (content_record_id, version_number, content, created_by) VALUES
    (1, 1, '{"headline_medium": "Mallorca Beach Walk",    "body_medium": "Discover the hidden coves of Mallorca''s northwest coast.", "button_label": "Read more", "image_url": "/static/img/mallorca.jpg"}', 'seed'),
    (2, 1, '{"headline_medium": "Rome City Weekend",      "body_medium": "Three days in Rome without the tourist traps.",              "button_label": "Read more", "image_url": "/static/img/rome.jpg"}',     'seed'),
    (3, 1, '{"headline_medium": "Tenerife Nature Escape", "body_medium": "Teide at sunrise, laurel forest hikes in Anaga.",            "button_label": "Read more", "image_url": "/static/img/tenerife.jpg"}', 'seed');

-- =========================================================
-- CATEGORIES
-- =========================================================

INSERT INTO categories (name, type, parent_category_id) VALUES
    ('Beach',   'main', NULL),
    ('City',    'main', NULL),
    ('Nature',  'main', NULL),
    ('Hiking',  'sub',  NULL),
    ('Family',  'sub',  NULL),
    ('Culture', 'sub',  NULL);

INSERT INTO category_relations (parent_category_id, child_category_id, relation_type)
SELECT p.id, c.id, 'parent_child'
FROM categories p
JOIN categories c ON (
    (p.name = 'Nature' AND c.name = 'Hiking')
    OR (p.name = 'Beach'  AND c.name = 'Family')
    OR (p.name = 'City'   AND c.name = 'Family')
    OR (p.name = 'City'   AND c.name = 'Culture')
    OR (p.name = 'Nature' AND c.name = 'Culture')
);

INSERT INTO content_category_assignments (content_id, category_id, score)
SELECT v.content_id, cat.id, v.score
FROM (VALUES
    (1, 'Beach',   10),
    (1, 'Family',   7),
    (2, 'City',    10),
    (2, 'Culture',  9),
    (3, 'Nature',  10),
    (3, 'Hiking',   8)
) AS v(content_id, category_name, score)
JOIN categories cat ON cat.name = v.category_name;

-- =========================================================
-- RECIPIENTS
-- =========================================================

INSERT INTO recipients (external_id, email, language, preferred_airport, attributes, status) VALUES
    ('r-001', 'anna.mueller@example.com',  'de', 'HAM', '{"firstname": "Anna",   "lastname": "Müller"}',   'active'),
    ('r-002', 'jan.devries@example.com',   'nl', 'AMS', '{"firstname": "Jan",    "lastname": "de Vries"}', 'active'),
    ('r-003', 'sophie.martin@example.com', 'fr', 'CDG', '{"firstname": "Sophie", "lastname": "Martin"}',   'active');

-- Anna: beach-leaning | Jan: city/culture | Sophie: nature/city
INSERT INTO recipient_preferences (recipient_id, category_id, score, source)
SELECT r.id, cat.id, v.score, 'seed'
FROM (VALUES
    ('r-001', 'Beach',   90),
    ('r-001', 'Nature',  50),
    ('r-001', 'Family',  60),
    ('r-002', 'City',    85),
    ('r-002', 'Culture', 80),
    ('r-002', 'Family',  40),
    ('r-003', 'Nature',  75),
    ('r-003', 'City',    70),
    ('r-003', 'Hiking',  65)
) AS v(external_id, category_name, score)
JOIN recipients r   ON r.external_id = v.external_id
JOIN categories cat ON cat.name = v.category_name;

-- =========================================================
-- CAMPAIGN + VARIANTS + STRUCTURE
-- =========================================================

INSERT INTO campaigns (name, status) VALUES
    ('Summer 2026 Newsletter', 'draft');

INSERT INTO variants (campaign_id, name, status) VALUES
    (1, 'Variant A — Beach Focus', 'draft'),
    (1, 'Variant B — City Focus',  'draft');

INSERT INTO decision_slots (variant_id, name, decision_type, decision_strategy, candidate_filter, strategy_config, max_results) VALUES
    (1, 'Main Content Slot', 'content_recommendation', 'recipient_top_score',
     '{"category_ids": [1, 2, 3, 4, 5, 6]}',
     '{"content_score_weight": 1, "preference_score_weight": 10}', 1),
    (2, 'Main Content Slot', 'content_recommendation', 'recipient_top_score',
     '{"category_ids": [1, 2, 3, 4, 5, 6]}',
     '{"content_score_weight": 1, "preference_score_weight": 10}', 1);

INSERT INTO module_instances (variant_id, module_type, position, content_record_id, module_data, decision_slot_id) VALUES
    (1, 'hero',         1, 1,    '{"headline": "Your Summer Starts Here"}', NULL),
    (1, 'content_card', 2, NULL, NULL,                                       1),
    (1, 'cta',          3, NULL, '{"button_label": "Plan my trip"}',         NULL),
    (2, 'hero',         1, 2,    '{"headline": "City Escapes 2026"}',        NULL),
    (2, 'content_card', 2, NULL, NULL,                                       2),
    (2, 'cta',          3, NULL, '{"button_label": "Explore cities"}',       NULL);

-- =========================================================
-- SNAPSHOTS  (must come before send_instances)
-- =========================================================

INSERT INTO snapshots (variant_id, recipient_id, html_storage_type, html_location, html_size) VALUES
    (1, NULL, 'file', 'snapshots/variant_1_seed.html', 4096),
    (2, NULL, 'file', 'snapshots/variant_2_seed.html', 4200);

-- =========================================================
-- SEND + DELIVERY
-- =========================================================

INSERT INTO send_instances (snapshot_id, name, status, provider, scheduled_at) VALUES
    (1, 'Main send — Summer 2026', 'sent', 'mock', NOW() - INTERVAL '3 days');

INSERT INTO delivery_executions (send_instance_id, recipient_id, status, provider, provider_message_id) VALUES
    (1, 'r-001', 'delivered', 'mock', 'mock-msg-001'),
    (1, 'r-002', 'delivered', 'mock', 'mock-msg-002'),
    (1, 'r-003', 'delivered', 'mock', 'mock-msg-003');

-- Anna opened + clicked; Jan opened only; Sophie no engagement
INSERT INTO engagement_events (delivery_execution_id, event_type, provider, provider_event_id, event_data, occurred_at) VALUES
    (1, 'open',  'mock', 'evt-001', '{"user_agent": "Mozilla/5.0"}',        NOW() - INTERVAL '2 days'),
    (1, 'click', 'mock', 'evt-002', '{"url": "/trips/mallorca-beach-walk"}', NOW() - INTERVAL '2 days'),
    (2, 'open',  'mock', 'evt-003', '{"user_agent": "AppleMail/16.0"}',      NOW() - INTERVAL '2 days');

-- Anna's beach preference bumped after her click
INSERT INTO preference_update_logs (recipient_id, category_id, event_id, previous_score, delta, new_score, reason)
SELECT r.id, cat.id, 2, 90, 5, 95, 'click on beach content'
FROM recipients r
JOIN categories cat ON cat.name = 'Beach'
WHERE r.external_id = 'r-001';

-- =========================================================
-- DECISION RESOLUTIONS
-- =========================================================

INSERT INTO decision_resolutions (decision_slot_id, recipient_id, content_record_id, reason, score)
SELECT 1, r.id, 1, 'top preference match: Beach',  900 FROM recipients r WHERE r.external_id = 'r-001' UNION ALL
SELECT 1, r.id, 2, 'top preference match: City',   850 FROM recipients r WHERE r.external_id = 'r-002' UNION ALL
SELECT 1, r.id, 3, 'top preference match: Nature', 750 FROM recipients r WHERE r.external_id = 'r-003';

-- =========================================================
-- OVERRIDE EVENTS
-- =========================================================

INSERT INTO override_events (
    override_type, module_instance_id, decision_slot_id, send_instance_id,
    system_content_record_id, override_content_record_id,
    overridden_by, reason, outcome_delta, created_at
) VALUES
    -- Pending: manager swapped content on slot 1, outcome not yet recorded
    ('content', 2, 1, 1, 1, 2,
     'manager@example.com', 'City weekend fits the spring campaign better',
     NULL, NOW() - INTERVAL '4 days'),
    -- Resolved: earlier override on slot 2, outcome shows system was better
    ('content', 5, 2, 1, 3, 2,
     'manager@example.com', NULL,
     '{"system_open_rate": 0.21, "override_open_rate": 0.18, "system_click_rate": 0.04, "override_click_rate": 0.03}',
     NOW() - INTERVAL '10 days');

COMMIT;
