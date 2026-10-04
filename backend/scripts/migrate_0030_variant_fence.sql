-- migrate_0030_variant_fence.sql
--
-- task-254, ADR-180 and its 2026-10-04 addendum. A variant carries an
-- advisory fence: who last edited it and when. Every composer write sets it;
-- it lapses 30 minutes after the last edit; a person may clear any fence, a
-- machine only its own, and a machine's write across another actor's active
-- fence is refused. The label is the readable name (as content_overrides.
-- overridden_by); audit_events keeps the id-based record (ADR-153).
--
-- Safe to re-run.

BEGIN;
ALTER TABLE variants ADD COLUMN IF NOT EXISTS fenced_by_type varchar(20);
ALTER TABLE variants ADD COLUMN IF NOT EXISTS fenced_by_id integer;
ALTER TABLE variants ADD COLUMN IF NOT EXISTS fenced_by_label varchar(255);
ALTER TABLE variants ADD COLUMN IF NOT EXISTS fenced_at timestamptz;
COMMIT;
