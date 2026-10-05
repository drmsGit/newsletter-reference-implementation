-- migrate_0031_category_score_range.sql
--
-- task-278, ADR-080's addendum of 2026-10-04: a category score is a whole
-- number from 1 (barely in the category) to 10 (squarely), for every caller.
-- Nothing enforced it: the service refused only 0, the CSV import clamped and
-- the Jinja form allowed 1-100. Decided with the user 2026-10-05: the database
-- holds the rule, so no code path, present or future, can store a bad score.
--
-- **Existing rows outside the range are reported, never changed.** If any
-- exist, this migration stops with their ids and scores and alters nothing; a
-- person fixes them and runs it again. (The development database held none on
-- 2026-10-05.)
--
-- Safe to re-run.

DO $$
DECLARE
    offending text;
BEGIN
    SELECT string_agg(
               format('assignment %s (record %s, category %s): score %s',
                      id, content_id, category_id, score),
               '; ' ORDER BY id)
      INTO offending
      FROM content_category_assignments
     WHERE score < 1 OR score > 10;

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION 'category scores outside 1-10, fix these first (nothing was changed): %', offending;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'ck_content_category_assignments_score_range') THEN
        ALTER TABLE content_category_assignments
            ADD CONSTRAINT ck_content_category_assignments_score_range
            CHECK (score BETWEEN 1 AND 10);
    END IF;
END $$;
