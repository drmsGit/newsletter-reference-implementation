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
--   - 2 override events (1 pending outcome, 1 resolved)
--   - No snapshots/send/delivery seeded — create snapshots via UI after seeding

BEGIN;

-- CASCADE handles FK order automatically
TRUNCATE TABLE
    preference_update_logs,
    engagement_events,
    delivery_executions,
    content_overrides,
    decision_resolutions,
    consent_sync_logs,
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

INSERT INTO content_records (title, description, content, status) VALUES
    ('Mallorca Beach Walk',    'Discover the hidden coves of Mallorca''s northwest coast — a 12km walk between Port de Sóller and Sa Calobra.',
     '{"headline_medium": "Mallorca Beach Walk", "body_medium": "Discover the hidden coves of Mallorca''s northwest coast.", "button_label": "Read more", "image_url": "/static/img/mallorca.jpg"}', 'active'),
    ('Rome City Weekend',      'Three days in Rome without the tourist traps: neighbourhood trattorias, the Trastevere market, and a private tour of the Borghese Gallery.',
     '{"headline_medium": "Rome City Weekend", "body_medium": "Three days in Rome without the tourist traps.", "button_label": "Read more", "image_url": "/static/img/rome.jpg"}', 'active'),
    ('Tenerife Nature Escape', 'Teide at sunrise, laurel forest hikes in Anaga, and the star-gazing plateau of El Médano — Tenerife beyond the resorts.',
     '{"headline_medium": "Tenerife Nature Escape", "body_medium": "Teide at sunrise, laurel forest hikes in Anaga.", "button_label": "Read more", "image_url": "/static/img/tenerife.jpg"}', 'active');

INSERT INTO content_versions (content_record_id, version_number, content, created_by) VALUES
    (1, 1, '{"headline_medium": "Mallorca Beach Walk",    "body_medium": "Discover the hidden coves of Mallorca''s northwest coast.", "button_label": "Read more", "image_url": "/static/img/mallorca.jpg"}', 'seed'),
    (2, 1, '{"headline_medium": "Rome City Weekend",      "body_medium": "Three days in Rome without the tourist traps.",              "button_label": "Read more", "image_url": "/static/img/rome.jpg"}',     'seed'),
    (3, 1, '{"headline_medium": "Tenerife Nature Escape", "body_medium": "Teide at sunrise, laurel forest hikes in Anaga.",            "button_label": "Read more", "image_url": "/static/img/tenerife.jpg"}', 'seed');

-- =========================================================
-- CATEGORIES
-- =========================================================

-- Hierarchy lives entirely in category_relations (below); CategoryDB.parent_category_id
-- was dropped when the two competing hierarchy mechanisms were consolidated (Content Q5).
INSERT INTO categories (name, type) VALUES
    ('Beach',   'main'),
    ('City',    'main'),
    ('Nature',  'main'),
    ('Hiking',  'sub'),
    ('Family',  'sub'),
    ('Culture', 'sub');

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

-- consent_status is CRM-sourced; seed recipients are opted_in so the
-- end-to-end demo (audience resolution → decisioning → send) works out of the box.
INSERT INTO recipients (external_id, email, language, attributes, status, consent_status) VALUES
    ('r-001', 'anna.mueller@example.com',  'de', '{"firstname": "Anna",   "lastname": "Müller",   "preferred_airport": "HAM"}', 'active', 'opted_in'),
    ('r-002', 'jan.devries@example.com',   'nl', '{"firstname": "Jan",    "lastname": "de Vries", "preferred_airport": "AMS"}', 'active', 'opted_in'),
    ('r-003', 'sophie.martin@example.com', 'fr', '{"firstname": "Sophie", "lastname": "Martin",    "preferred_airport": "CDG"}', 'active', 'opted_in');

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

-- name is the internal label; subject/preheader are the recipient-facing copy
-- used at send time (never the send_instance label).
INSERT INTO variants (campaign_id, name, subject, preheader, status) VALUES
    (1, 'Variant A — Beach Focus', 'Your summer beach escape awaits', 'Hidden coves, quiet walks, and warm water', 'draft'),
    (1, 'Variant B — City Focus',  'City weekends made for wandering', 'Trattorias, markets, and backstreets',      'draft');

INSERT INTO decision_slots (variant_id, name, decision_type, decision_strategy, candidate_filter, strategy_config, max_results) VALUES
    (1, 'Main Content Slot', 'content_recommendation', 'recipient_top_score',
     '{"category_ids": [1, 2, 3, 4, 5, 6]}',
     '{"content_score_weight": 1, "preference_score_weight": 10}', 1),
    (2, 'Main Content Slot', 'content_recommendation', 'recipient_top_score',
     '{"category_ids": [1, 2, 3, 4, 5, 6]}',
     '{"content_score_weight": 1, "preference_score_weight": 10}', 1);

-- The decision-driven module uses img_left (a real cms:true manifest that
-- renders headline_medium/body_medium/image_url) so the per-recipient
-- personalization — and any content override applied on top — is actually
-- visible. (It was 'content_card', which has no manifest and renders nothing.)
INSERT INTO module_instances (variant_id, module_type, position, content_record_id, module_data, decision_slot_id) VALUES
    (1, 'hero',     1, 1,    '{"headline": "Your Summer Starts Here"}', NULL),
    (1, 'img_left', 2, NULL, NULL,                                       1),
    (1, 'cta',      3, NULL, '{"button_label": "Plan my trip"}',         NULL),
    (2, 'hero',     1, 2,    '{"headline": "City Escapes 2026"}',        NULL),
    (2, 'img_left', 2, NULL, NULL,                                       2),
    (2, 'cta',      3, NULL, '{"button_label": "Explore cities"}',       NULL);

-- =========================================================
-- SNAPSHOTS / SEND / DELIVERY
-- =========================================================
-- Omitted from seed: snapshots require rendered HTML whose storage
-- strategy is not yet decided (file vs DB vs object storage).
-- Create snapshots through the UI after seeding.

-- Preference-bump seed row intentionally omitted: PreferenceUpdateLogDB.event_id is NOT NULL
-- and always traces to a real EngagementEventDB row, which itself requires a delivery_execution
-- (which requires a send_instance + snapshot) — a chain this seed deliberately doesn't build.
-- See docs/backlog.md "Needs ADR" (snapshot/HTML storage strategy) for the full context.

-- =========================================================
-- DECISION RESOLUTIONS
-- =========================================================

INSERT INTO decision_resolutions (decision_slot_id, recipient_id, content_record_id, reason, score)
SELECT 1, r.id, 1, 'top preference match: Beach',  900 FROM recipients r WHERE r.external_id = 'r-001' UNION ALL
SELECT 1, r.id, 2, 'top preference match: City',   850 FROM recipients r WHERE r.external_id = 'r-002' UNION ALL
SELECT 1, r.id, 3, 'top preference match: Nature', 750 FROM recipients r WHERE r.external_id = 'r-003';

-- =========================================================
-- CONTENT OVERRIDES  (the functional override layer, ADR-040/041)
-- =========================================================
-- Both target module 2 (variant 1's img_left, personalized via slot 1).
-- Row 1 is the ACTIVE override rendering honors; row 2 is reverted history.

INSERT INTO content_overrides (
    module_instance_id, override_content_record_id, field_overrides,
    system_content_record_id, send_instance_id,
    overridden_by, reason, active, reverted_at, outcome_delta, created_at
) VALUES
    -- Active field-level override: unify the headline across the personalized
    -- picks for this send (the common "the resolved headline is wrong/too long
    -- for this newsletter" case). Body/image stay per-recipient.
    (2, NULL, '{"headline_medium": "Editor''s pick of the week"}',
     NULL, NULL,
     'manager@example.com', 'Consistent headline across this send''s personalized picks',
     true, NULL, NULL, NOW() - INTERVAL '4 days'),
    -- Reverted record-pin (history): manager once forced Rome for everyone;
    -- the outcome showed the system's personalization performed better, so it
    -- was reset. This is the trust-loop artifact ("did the override outperform?").
    (2, 2, NULL,
     1, NULL,
     'manager@example.com', 'Tried forcing Rome for all — reverted after review',
     false, NOW() - INTERVAL '6 days',
     '{"system_open_rate": 0.21, "override_open_rate": 0.18, "system_click_rate": 0.04, "override_click_rate": 0.03}',
     NOW() - INTERVAL '10 days');

COMMIT;
