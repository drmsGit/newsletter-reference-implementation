-- migrate_0001a_consent_expand.sql
--
-- ADR-163 (Per-Channel Consent and Addressability), phase A — EXPAND half.
--
-- Introduces the append-only `consent_events` log keyed (recipient, channel,
-- purpose) and `recipient_addresses` as the addressability store, and
-- backfills both from the columns they replace.
--
-- THIS SCRIPT IS PURELY ADDITIVE. It drops nothing. `recipients.consent_status`
-- and the old `consent_sync_logs` columns are still present and still readable
-- after it runs, so the application keeps working unchanged. Removing them is
-- `migrate_0001b_consent_contract.sql`, which must not run until no code reads
-- them any more.
--
-- Expand/contract, rather than one script, because the alternative is a window
-- where the schema has moved and the code has not — and the code in question is
-- the consent gate, i.e. the one place where being briefly wrong is a
-- compliance incident rather than a bug.
--
-- PHASE A ONLY. `recipients.email` is populated into `recipient_addresses` but
-- is not dropped even by the contract half — the ~22 display sites that read
-- the column move in phase B.
--
-- Why this file exists at all: this repository has no Alembic and no migration
-- runner. `Base.metadata.create_all()` creates missing tables and never alters
-- or drops anything, so schema change has to be written by hand. Decided
-- 2026-09-12: hand-written, numbered, idempotent DDL in scripts/, consistent
-- with how reset_all_data.sql already works.
--
-- Idempotent: safe to run twice. Backfills are NOT EXISTS-guarded rather than
-- blind inserts, and the statements that reference columns the contract half
-- later removes are wrapped in dynamic SQL — a plain statement is resolved at
-- PARSE time, so an information_schema guard in a WHERE clause does not save
-- it once the column is gone.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0001a_consent_expand.sql
--
-- Verify afterwards with the block at the bottom, which prints row counts and
-- refuses to leave you guessing whether the backfill covered everyone.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. consent_events — the append-only grid
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS consent_events (
    id              SERIAL PRIMARY KEY,
    recipient_id    INTEGER NOT NULL REFERENCES recipients(id),
    channel         VARCHAR(50)  NOT NULL DEFAULT 'email',
    purpose         VARCHAR(50)  NOT NULL DEFAULT 'marketing',
    status          VARCHAR(50)  NOT NULL,
    source          VARCHAR(100) NOT NULL,
    note            TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_consent_events_recipient_id
    ON consent_events (recipient_id);

-- The read is always "latest row for this cell", so the index carries the
-- ordering as well as the lookup.
CREATE INDEX IF NOT EXISTS ix_consent_events_cell_latest
    ON consent_events (recipient_id, channel, purpose, created_at);

-- ---------------------------------------------------------------------------
-- 2. recipient_addresses — addressability
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recipient_addresses (
    id              SERIAL PRIMARY KEY,
    recipient_id    INTEGER NOT NULL REFERENCES recipients(id),
    channel         VARCHAR(50) NOT NULL DEFAULT 'email',
    value           JSON        NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
    is_primary      BOOLEAN     NOT NULL DEFAULT FALSE,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_recipient_addresses_recipient_id
    ON recipient_addresses (recipient_id);

CREATE INDEX IF NOT EXISTS ix_recipient_addresses_channel
    ON recipient_addresses (recipient_id, channel, status);

-- Deliberately NO unique constraint on (channel, value): two recipients
-- legitimately sharing an address is a real case — shared team inboxes,
-- info@, a household — and forbidding it would reject CRM data the platform
-- accepts today. Deduplication happens in stage 1 of the exclusion stack and
-- is recorded there (ADR-163 addendum 2026-09-12, point 3).

-- ---------------------------------------------------------------------------
-- 3. delivery_executions gains channel + purpose
-- ---------------------------------------------------------------------------
-- Denormalized at plan time so an inbound bounce/complaint webhook has both
-- dimensions without a four-join chain back to the variant
-- (ADR-163 addendum 2026-09-12, point 1).

ALTER TABLE delivery_executions
    ADD COLUMN IF NOT EXISTS channel VARCHAR(50) NOT NULL DEFAULT 'email';

ALTER TABLE delivery_executions
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(50) NOT NULL DEFAULT 'marketing';

-- ---------------------------------------------------------------------------
-- 4. Backfill consent_events from recipients.consent_status
-- ---------------------------------------------------------------------------
-- Everything existing is email/marketing: that is the only channel and the
-- only purpose the system has had. source='migration' rather than 'crm',
-- because asserting the CRM said this would be inventing evidence — and
-- consent evidence is the thing this table exists to be able to prove.
--
-- created_at takes the recipient's updated_at, the closest thing to "when this
-- status was last set" that the old schema retained.

-- Wrapped in dynamic SQL deliberately. A plain statement referencing
-- r.consent_status is resolved at PARSE time, so an `information_schema` guard
-- in the WHERE clause does not save it — once migrate_0001b has dropped the
-- column, re-running this script would fail to parse before the guard is ever
-- evaluated. EXECUTE defers parsing until we know the column is there.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recipients' AND column_name = 'consent_status'
    ) THEN
        EXECUTE $sql$
            INSERT INTO consent_events
                (recipient_id, channel, purpose, status, source, note, created_at)
            SELECT
                r.id,
                'email',
                'marketing',
                r.consent_status,
                'migration',
                'backfilled from recipients.consent_status (ADR-163 phase A)',
                COALESCE(r.updated_at, r.created_at, now())
            FROM recipients r
            WHERE NOT EXISTS (
                SELECT 1 FROM consent_events e
                WHERE e.recipient_id = r.id
                  AND e.channel = 'email'
                  AND e.purpose = 'marketing'
            )
        $sql$;
    END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- 5. Backfill recipient_addresses from recipients.email
-- ---------------------------------------------------------------------------
-- is_primary = TRUE because it is the person's only address; verified_at is
-- left NULL, since nothing in the old schema ever verified it and recording a
-- verification that did not happen would be the same invention as above.

INSERT INTO recipient_addresses (recipient_id, channel, value, status, is_primary, created_at, updated_at)
SELECT
    r.id,
    'email',
    json_build_object('email', r.email),
    CASE WHEN r.status = 'active' THEN 'active' ELSE 'inactive' END,
    TRUE,
    COALESCE(r.created_at, now()),
    COALESCE(r.updated_at, now())
FROM recipients r
WHERE r.email IS NOT NULL
  AND r.email <> ''
  AND NOT EXISTS (
        SELECT 1 FROM recipient_addresses a
        WHERE a.recipient_id = r.id
          AND a.channel = 'email'
      );

-- ---------------------------------------------------------------------------
-- 6. consent_sync_logs sheds its consent values
-- ---------------------------------------------------------------------------
-- It held crm_consent_status and platform_status_before only because consent
-- was one mutable column with no history to diff against. The CRM's assertion
-- is now an event with source='crm', so keeping them here would be one fact in
-- two places (ADR-163 addendum 2026-09-12, point 2).
--
-- The old asserted values are migrated into consent_events first, so the
-- evidence is moved rather than discarded.

ALTER TABLE consent_sync_logs
    ADD COLUMN IF NOT EXISTS ok BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE consent_sync_logs
    ADD COLUMN IF NOT EXISTS changes_applied INTEGER NOT NULL DEFAULT 0;

-- Relax the columns the contract half will drop. Expanding is not only adding:
-- between the two halves, the new code no longer writes crm_consent_status or
-- platform_status_before, and a NOT NULL they no longer populate would make
-- every sync fail. Dropping a NOT NULL destroys nothing and is reversible;
-- leaving it in place would mean the schema and the code cannot both be right
-- at the same time, which is the whole condition expand/contract exists to
-- avoid.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'consent_sync_logs' AND column_name = 'crm_consent_status'
    ) THEN
        EXECUTE 'ALTER TABLE consent_sync_logs ALTER COLUMN crm_consent_status DROP NOT NULL';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'consent_sync_logs' AND column_name = 'platform_status_before'
    ) THEN
        EXECUTE 'ALTER TABLE consent_sync_logs ALTER COLUMN platform_status_before DROP NOT NULL';
    END IF;
    -- `applied` needs the same treatment for a subtler reason: its NOT NULL was
    -- satisfied by a *Python-side* SQLAlchemy default, never a database one, so
    -- the constraint was only ever met by the ORM remembering to fill it in.
    -- With the column gone from the model, nothing does.
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'consent_sync_logs' AND column_name = 'applied'
    ) THEN
        EXECUTE 'ALTER TABLE consent_sync_logs ALTER COLUMN applied DROP NOT NULL';
    END IF;
END
$$;

-- Dynamic SQL for the same parse-time reason as step 4.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'consent_sync_logs' AND column_name = 'crm_consent_status'
    ) THEN
        EXECUTE $sql$
            INSERT INTO consent_events
                (recipient_id, channel, purpose, status, source, note, created_at)
            SELECT
                l.recipient_id,
                'email',
                'marketing',
                l.crm_consent_status,
                'crm',
                'migrated from consent_sync_logs (ADR-163 phase A)',
                l.synced_at
            FROM consent_sync_logs l
            WHERE l.recipient_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM consent_events e
                  WHERE e.recipient_id = l.recipient_id
                    AND e.source = 'crm'
                    AND e.created_at = l.synced_at
              )
        $sql$;
    END IF;

    -- `applied` (boolean, "was the asserted value written") becomes changes_applied.
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'consent_sync_logs' AND column_name = 'applied'
    ) THEN
        EXECUTE $sql$
            UPDATE consent_sync_logs
            SET changes_applied = CASE WHEN applied THEN 1 ELSE 0 END
            WHERE changes_applied = 0
        $sql$;
    END IF;
END
$$;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification — run this after, and read it.
-- ---------------------------------------------------------------------------
-- Every recipient must have exactly one email/marketing consent cell and at
-- least one email address, or resolution will silently drop them once the
-- service layer reads these tables.

\echo ''
\echo '--- migrate_0001a (expand) verification ---'

SELECT
    (SELECT count(*) FROM recipients)                                AS recipients,
    (SELECT count(*) FROM consent_events)                            AS consent_events,
    (SELECT count(*) FROM recipient_addresses)                       AS addresses,
    (SELECT count(*) FROM recipients r WHERE NOT EXISTS (
        SELECT 1 FROM consent_events e WHERE e.recipient_id = r.id))  AS recipients_without_consent,
    (SELECT count(*) FROM recipients r WHERE NOT EXISTS (
        SELECT 1 FROM recipient_addresses a WHERE a.recipient_id = r.id)) AS recipients_without_address;

\echo 'recipients_without_consent and recipients_without_address must both be 0.'
\echo 'Nothing was dropped. Run migrate_0001b only once no code reads the old columns.'
\echo ''
