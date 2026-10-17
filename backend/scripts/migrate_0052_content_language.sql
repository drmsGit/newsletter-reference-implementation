-- migrate_0052_content_language.sql
--
-- task-369, [[ADR-200 — A Content Record Has a Language, and a Translation Is a Linked Record]]:
-- a record's language, and translations as linked records.
--   * content_records.language: chosen from the brand's profile languages, or
--     NULL (not set: eligible in every language). Existing records stay NULL.
--   * content_records.translation_of_id: the original a translation was made
--     from. Deleting the original leaves the translation standing, unlinked.
--   * content_records.translated_from: per field, the original's text the
--     translation's text was made from, so a changed original shows per field.
--   * one translation per original per language.
--   * ai_runs.input_snapshot: what a run read of the platform's own content
--     (a translation run's original text), so taking a field records the text
--     it was translated from. Never a pasted source (ADR-141 addendum 2026-10-16).
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE content_records ADD COLUMN IF NOT EXISTS language VARCHAR(20);
ALTER TABLE content_records ADD COLUMN IF NOT EXISTS translation_of_id INTEGER
    REFERENCES content_records(id) ON DELETE SET NULL;
ALTER TABLE content_records ADD COLUMN IF NOT EXISTS translated_from JSON;

CREATE UNIQUE INDEX IF NOT EXISTS uq_content_translation_language
    ON content_records (translation_of_id, language)
    WHERE translation_of_id IS NOT NULL;

ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS input_snapshot JSON;

COMMIT;
