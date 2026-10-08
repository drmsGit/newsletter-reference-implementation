-- migrate_0038_send_skip_without_resolution.sql
--
-- task-228, decided with the user 2026-09-28 and 2026-10-08 (ADR-086's
-- addendum of 2026-10-08): "Don't send if no slot resolved" is a choice per
-- send, set when it is planned, off by default. On, a recipient whose
-- personalised blocks all came up empty is skipped even though static
-- content rendered. Existing sends keep today's behaviour (off).
--
-- Safe to re-run.

ALTER TABLE send_instances
    ADD COLUMN IF NOT EXISTS skip_without_resolution BOOLEAN NOT NULL DEFAULT FALSE;
