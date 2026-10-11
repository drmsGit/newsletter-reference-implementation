-- migrate_0045_unattended_ceiling.sql
--
-- task-341, [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
-- addenda of 2026-10-09 and 2026-10-11: an integration's unattended sending
-- becomes a recipient ceiling instead of an on/off switch. 0 means never.
--
-- Integrations switched ON keep exactly what they had: their ceiling becomes
-- the company-wide recipient cap as it stands now (app_config
-- max_send_recipients, or the code default of 1000), so nothing changes for
-- them until someone lowers it. Switched OFF stays 0.
--
-- SAFE ON EXISTING DATA. Safe to re-run: the copy runs only while the old
-- column exists.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE integrations ADD COLUMN IF NOT EXISTS unattended_ceiling INTEGER NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'integrations' AND column_name = 'may_send_unattended') THEN
        UPDATE integrations
           SET unattended_ceiling = COALESCE(
                   (SELECT (value #>> '{}')::int FROM app_config WHERE key = 'max_send_recipients'),
                   1000)
         WHERE may_send_unattended;
        ALTER TABLE integrations DROP COLUMN may_send_unattended;
    END IF;
END $$;

COMMIT;
