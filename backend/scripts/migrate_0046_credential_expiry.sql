-- migrate_0046_credential_expiry.sql
--
-- task-344, [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
-- second addenda of 2026-10-09 and 2026-10-11: an integration's key may be
-- given an expiry, in days, when it is issued. Existing keys get none and
-- behave as before, until someone adds one.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE integration_credentials ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE integration_credentials ADD COLUMN IF NOT EXISTS expires_in_days INTEGER;

COMMIT;
