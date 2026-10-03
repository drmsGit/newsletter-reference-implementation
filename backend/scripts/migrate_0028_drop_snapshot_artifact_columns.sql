-- migrate_0028_drop_snapshot_artifact_columns.sql
--
-- task-247. ADR-183 point 5 stopped writing snapshot files on 2026-10-02: the
-- frame in `render_context` IS the snapshot, and a preview is rendered from it
-- on demand. Since then every row carried `artifact_storage_type = 'inline'`,
-- `artifact_location = 'inline:render_context'` (a placeholder, there only
-- because the column was NOT NULL) and `artifact_size` (the byte count of a
-- render that was computed and thrown away). Three columns describing a file
-- that does not exist.
--
-- Nothing is lost: no row's location ever pointed anywhere after point 5, and
-- rows from before it are frameless and refused at send (ADR-183 point 6).
--
-- Safe to re-run.

BEGIN;
ALTER TABLE snapshots DROP COLUMN IF EXISTS artifact_storage_type;
ALTER TABLE snapshots DROP COLUMN IF EXISTS artifact_location;
ALTER TABLE snapshots DROP COLUMN IF EXISTS artifact_size;
COMMIT;
