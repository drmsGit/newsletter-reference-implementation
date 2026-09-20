-- migrate_0019_snapshot_artifact_columns.sql
--
-- [[ADR-162 — Channel Rendering and Artifacts]] point 3. Rename three columns
-- on `snapshots`:
--
--     html_storage_type -> artifact_storage_type
--     html_location     -> artifact_location
--     html_size         -> artifact_size
--
-- **The storage decision is right and is not what changes here.** A push
-- artifact lives inline in the row rather than in a `.json` beside the `.html`
-- files, and that was decided deliberately on 2026-09-17. What was wrong is the
-- NAMES: a push payload's byte count returned in a field called `html_size` is,
-- in the interview's own words, "a lie the next reader has to decode".
--
-- **Why now, when the ADR named no trigger.** The trigger turned out to be a
-- second consumer of the OpenAPI schema. The React client's typed API client is
-- generated from it, so `html_size` would become the name every call site in
-- the frontend uses for push content — and renaming after that means
-- regenerating the client and touching all of them. Before the generator runs,
-- this is three columns and a handful of references.
--
-- **The open question the backlog attached to this is now answered.** It asked
-- whether `html_size` means the same thing across both storage branches. It
-- does: both write `artifact.size_bytes()` (`rendering/renderers/base.py:73`),
-- which is the UTF-8 byte length of the HTML body or of the JSON-serialised
-- fields. One meaning, two shapes — which is exactly why the neutral name is
-- the correct one and `html_size` was misleading rather than merely ugly.
--
-- Guarded per column so a partially-applied run finishes rather than failing,
-- and so re-running is a no-op.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'snapshots' AND column_name = 'html_storage_type'
    ) THEN
        ALTER TABLE snapshots RENAME COLUMN html_storage_type TO artifact_storage_type;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'snapshots' AND column_name = 'html_location'
    ) THEN
        ALTER TABLE snapshots RENAME COLUMN html_location TO artifact_location;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'snapshots' AND column_name = 'html_size'
    ) THEN
        ALTER TABLE snapshots RENAME COLUMN html_size TO artifact_size;
    END IF;
END $$;
