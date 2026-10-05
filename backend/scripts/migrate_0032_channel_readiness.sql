-- migrate_0032_channel_readiness.sql
--
-- task-283, ADR-174's and ADR-179's addenda of 2026-10-05 (decided with the
-- user, task-282).
--
-- 1. content_channel_readiness: one row per (content record, channel) that a
--    person marked ready, with who and when. Unmarking deletes the row; the
--    audit log keeps the history. A new channel costs no migration. No brand
--    column: the record carries it (ADR-172 point 5).
-- 2. content_records.machine_ready: may a machine pick this without a person
--    deciding? New records start false (fail closed).
--
-- **The backfills run once, in the step that creates the thing they fill.**
-- Re-running this file must not re-mark a record a person has since unmarked
-- or switched off:
--   - existing records become machine ready, because decision slots pick them
--     today and turning them all off would silently empty every slot;
--   - existing ACTIVE records are marked ready for email, the channel they were
--     written for and what slots pick today. Push is never assumed: a person
--     marks it.
--
-- Safe to re-run.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'content_records' AND column_name = 'machine_ready') THEN
        ALTER TABLE content_records ADD COLUMN machine_ready boolean NOT NULL DEFAULT false;
        UPDATE content_records SET machine_ready = true;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'content_channel_readiness') THEN
        CREATE TABLE content_channel_readiness (
            id serial PRIMARY KEY,
            content_id integer NOT NULL REFERENCES content_records(id),
            channel varchar(50) NOT NULL,
            marked_by varchar(255),
            marked_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_content_channel_readiness_content_channel UNIQUE (content_id, channel)
        );
        CREATE INDEX ix_content_channel_readiness_channel ON content_channel_readiness (channel);
        INSERT INTO content_channel_readiness (content_id, channel, marked_by)
            SELECT id, 'email', 'migration 0032 (was active before readiness existed)'
              FROM content_records WHERE status = 'active';
    END IF;
END $$;
