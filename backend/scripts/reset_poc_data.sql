-- TODO
-- Incomplete draft.
-- Missing:
-- - send instances
-- - delivery executions
-- - engagement events
-- - complete recipient test setup

BEGIN;

-- =========================================================
-- Reset dependent runtime data
-- =========================================================

DELETE FROM preference_update_logs;
DELETE FROM engagement_events;
DELETE FROM decision_resolutions;
DELETE FROM recipient_preferences;

-- =========================================================
-- Reset content/category links
-- =========================================================

DELETE FROM content_category_assignments;
DELETE FROM category_relations;

-- =========================================================
-- Reset categories
-- =========================================================

TRUNCATE TABLE categories RESTART IDENTITY CASCADE;

INSERT INTO categories (name, type, parent_category_id)
VALUES
  ('Beach', 'main', NULL),
  ('City', 'main', NULL),
  ('Nature', 'main', NULL),
  ('Hiking', 'sub', NULL),
  ('Family', 'sub', NULL),
  ('Culture', 'sub', NULL);

-- =========================================================
-- Category relations
-- =========================================================

INSERT INTO category_relations (
  parent_category_id,
  child_category_id,
  relation_type
)
SELECT p.id, c.id, 'parent_child'
FROM categories p
JOIN categories c
  ON (
    (p.name = 'Nature' AND c.name = 'Hiking')
    OR
    (p.name = 'Beach' AND c.name = 'Family')
    OR
    (p.name = 'City' AND c.name = 'Family')
    OR
    (p.name = 'City' AND c.name = 'Culture')
    OR
    (p.name = 'Nature' AND c.name = 'Culture')
  );

-- =========================================================
-- Content category assignments
-- =========================================================

INSERT INTO content_category_assignments (
  content_id,
  category_id,
  score
)
SELECT
  v.content_id,
  cat.id,
  v.score
FROM (
  VALUES
    (1, 'Beach', 10),
    (1, 'Family', 7),
    (2, 'City', 10),
    (2, 'Culture', 9),
    (3, 'Nature', 10),
    (3, 'Hiking', 8)
) AS v(content_id, category_name, score)
JOIN categories cat
  ON cat.name = v.category_name;

-- =========================================================
-- Recipient preferences for recipient-aware decision tests
-- =========================================================

INSERT INTO recipient_preferences (
  recipient_id,
  category_id,
  score,
  source
)
SELECT
  1,
  cat.id,
  v.score,
  'reset_seed'
FROM (
  VALUES
    ('Beach', 90),
    ('Nature', 70),
    ('Culture', 40)
) AS v(category_name, score)
JOIN categories cat
  ON cat.name = v.category_name;

-- =========================================================
-- Decision slot candidate filter reset
-- =========================================================

UPDATE decision_slots
SET
  candidate_filter = '{
    "category_ids": [1, 2, 3, 4, 5, 6]
  }'::json,
  strategy_config = '{
    "content_score_weight": 1,
    "preference_score_weight": 10
  }'::json
WHERE id = 1
  AND decision_strategy = 'recipient_top_score';

COMMIT;