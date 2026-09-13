-- migrate_0004_drop_recipient_email.sql
--
-- ADR-163 (Per-Channel Consent and Addressability), phase B.
--
-- Drops `recipients.email`. Its values have lived in `recipient_addresses`
-- since migrate_0001a backfilled them, and since phase B nothing reads the
-- column — every display site resolves the address through the point 11 rules
-- (primary flag, else most-recently-verified) instead.
--
-- DESTRUCTIVE AND ONE-WAY. Run it only when all three hold:
--   1. migrate_0001a has run and every recipient has an email address row;
--   2. no code reads `RecipientDB.email` — the model no longer declares it;
--   3. the suite passes.
--
-- The guard below enforces (1) rather than trusting it, and it is stricter
-- than 0001b's was: it refuses if ANY recipient would lose an address that is
-- not already represented in recipient_addresses, comparing the actual values
-- rather than merely counting rows. A recipient whose column and row disagree
-- is a migration bug, and dropping the column would destroy the evidence.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0004_drop_recipient_email.sql

BEGIN;

DO $$
DECLARE
    missing INTEGER;
    mismatched INTEGER;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recipients' AND column_name = 'email'
    ) THEN
        RAISE NOTICE 'recipients.email already dropped — nothing to do.';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'recipient_addresses'
    ) THEN
        RAISE EXCEPTION
            'recipient_addresses does not exist — run migrate_0001a first';
    END IF;

    -- Anyone with an address in the column but no row at all.
    EXECUTE $sql$
        SELECT count(*) FROM recipients r
        WHERE r.email IS NOT NULL AND r.email <> ''
          AND NOT EXISTS (
              SELECT 1 FROM recipient_addresses a
              WHERE a.recipient_id = r.id AND a.channel = 'email'
          )
    $sql$ INTO missing;

    IF missing > 0 THEN
        RAISE EXCEPTION
            '% recipient(s) have an email column value but no email address '
            'row. Dropping the column would destroy it. Re-run '
            'migrate_0001a_consent_expand.sql.', missing;
    END IF;

    -- Anyone whose column value appears in NO row for that channel. Catches a
    -- column updated after the backfill by code that has since been removed.
    EXECUTE $sql$
        SELECT count(*) FROM recipients r
        WHERE r.email IS NOT NULL AND r.email <> ''
          AND NOT EXISTS (
              SELECT 1 FROM recipient_addresses a
              WHERE a.recipient_id = r.id
                AND a.channel = 'email'
                AND a.value ->> 'email' = r.email
          )
    $sql$ INTO mismatched;

    IF mismatched > 0 THEN
        RAISE EXCEPTION
            '% recipient(s) have an email column value that no addressability '
            'row carries. That is a migration bug, not a stale column — '
            'investigate before dropping.', mismatched;
    END IF;

    RAISE NOTICE 'Guard passed: every email column value is represented in recipient_addresses.';
END
$$;

ALTER TABLE recipients DROP COLUMN IF EXISTS email;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0004 (phase B) verification ---'

SELECT
    (SELECT count(*) FROM information_schema.columns
       WHERE table_name = 'recipients' AND column_name = 'email')        AS email_col,
    (SELECT count(*) FROM recipients)                                    AS recipients,
    (SELECT count(*) FROM recipient_addresses WHERE channel = 'email')   AS email_addresses,
    (SELECT count(*) FROM recipients r WHERE NOT EXISTS (
        SELECT 1 FROM recipient_addresses a
        WHERE a.recipient_id = r.id AND a.channel = 'email'))            AS unreachable;

\echo 'email_col must be 0. unreachable counts recipients with no email address —'
\echo 'they are excluded at stage 1 of the send-time stack, which is correct.'
\echo ''
