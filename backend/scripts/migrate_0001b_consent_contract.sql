-- migrate_0001b_consent_contract.sql
--
-- ADR-163 (Per-Channel Consent and Addressability), phase A — CONTRACT half.
--
-- Removes the columns `migrate_0001a_consent_expand.sql` replaced:
--   * recipients.consent_status          → consent_events
--   * consent_sync_logs.crm_consent_status
--   * consent_sync_logs.platform_status_before
--   * consent_sync_logs.applied          → changes_applied
--
-- DESTRUCTIVE AND ONE-WAY. Run it only when all three conditions hold:
--   1. migrate_0001a has run and its verification showed zero recipients
--      without a consent cell and zero without an address;
--   2. no code reads `RecipientDB.consent_status` any more — the three gates
--      (find_by_criteria, resolve_audience's consent floor, and
--      execute_decision_slot) read consent_events instead;
--   3. tests/test_consent_gates.py passes against the expanded schema.
--
-- `recipients.email` is NOT dropped here. That is phase B, together with the
-- ~22 display sites that read it.
--
-- The guard below enforces (1) rather than trusting it: if any recipient would
-- lose their consent state, the script aborts instead of dropping the column.
-- There is no undo — the old value exists only in consent_events afterwards.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0001b_consent_contract.sql
--
-- Idempotent: safe to run twice (every drop is IF EXISTS, and the guard skips
-- cleanly once the column is already gone).

BEGIN;

-- ---------------------------------------------------------------------------
-- Guard — refuse to drop anything that has not been migrated
-- ---------------------------------------------------------------------------
-- Checked inside the transaction, so a RAISE rolls the whole thing back.

DO $$
DECLARE
    missing_consent INTEGER;
    missing_address INTEGER;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recipients' AND column_name = 'consent_status'
    ) THEN
        RAISE NOTICE 'recipients.consent_status already dropped — nothing to contract.';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'consent_events'
    ) THEN
        RAISE EXCEPTION
            'consent_events does not exist — run migrate_0001a_consent_expand.sql first';
    END IF;

    SELECT count(*) INTO missing_consent
    FROM recipients r
    WHERE NOT EXISTS (
        SELECT 1 FROM consent_events e WHERE e.recipient_id = r.id
    );

    SELECT count(*) INTO missing_address
    FROM recipients r
    WHERE r.email IS NOT NULL AND r.email <> ''
      AND NOT EXISTS (
        SELECT 1 FROM recipient_addresses a WHERE a.recipient_id = r.id
      );

    IF missing_consent > 0 THEN
        RAISE EXCEPTION
            '% recipient(s) have no consent event — dropping consent_status would '
            'destroy their consent state. Re-run migrate_0001a_consent_expand.sql.',
            missing_consent;
    END IF;

    IF missing_address > 0 THEN
        RAISE EXCEPTION
            '% recipient(s) have an email but no addressability row — '
            'run migrate_0001a_consent_expand.sql first.',
            missing_address;
    END IF;

    RAISE NOTICE 'Guard passed: every recipient has a consent event and an address.';
END
$$;

-- ---------------------------------------------------------------------------
-- 1. consent_sync_logs sheds its consent values
-- ---------------------------------------------------------------------------
-- It held crm_consent_status and platform_status_before only because consent
-- was one mutable column with no history to diff against. The CRM's assertion
-- is now an event with source='crm', so keeping them would be one fact in two
-- places, free to disagree (ADR-163 addendum 2026-09-12, point 2).
-- migrate_0001a already copied those asserted values into consent_events.

ALTER TABLE consent_sync_logs DROP COLUMN IF EXISTS crm_consent_status;
ALTER TABLE consent_sync_logs DROP COLUMN IF EXISTS platform_status_before;
ALTER TABLE consent_sync_logs DROP COLUMN IF EXISTS applied;

-- recipient_id / external_id become nullable: a sync that could not be matched
-- to a recipient is exactly the kind of run worth recording.
ALTER TABLE consent_sync_logs ALTER COLUMN recipient_id DROP NOT NULL;
ALTER TABLE consent_sync_logs ALTER COLUMN external_id  DROP NOT NULL;

-- ---------------------------------------------------------------------------
-- 2. Drop recipients.consent_status
-- ---------------------------------------------------------------------------
-- The gate that stood on this column for two months. Its values now live in
-- consent_events, keyed (recipient, channel, purpose), where they carry a
-- source and a timestamp and can survive an erasure in minimised form.

ALTER TABLE recipients DROP COLUMN IF EXISTS consent_status;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0001b (contract) verification ---'

SELECT
    (SELECT count(*) FROM information_schema.columns
       WHERE table_name = 'recipients' AND column_name = 'consent_status')  AS consent_status_col,
    (SELECT count(*) FROM information_schema.columns
       WHERE table_name = 'recipients' AND column_name = 'email')           AS email_col_phase_b,
    (SELECT count(*) FROM consent_events)                                   AS consent_events,
    (SELECT count(DISTINCT recipient_id) FROM consent_events)               AS recipients_with_consent;

\echo 'consent_status_col must be 0. email_col_phase_b must still be 1 (phase B drops it).'
\echo ''
