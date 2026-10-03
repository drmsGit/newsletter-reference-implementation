-- migrate_0029_content_record_updated_at.sql
--
-- task-257. A content record gets a version token, as campaigns, variants,
-- modules and slots already have (ADR-180 point 2): the variant editor saves
-- catalogue fields on blur (campaign write surface design pass, D1), and
-- without a token two managers editing one record silently overwrite each
-- other. Existing rows take the time of this migration; nothing older is
-- known about them.
--
-- Safe to re-run.

BEGIN;
ALTER TABLE content_records
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
COMMIT;
