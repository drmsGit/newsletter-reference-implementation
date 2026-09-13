-- migrate_0005_login_code_requests.sql
--
-- Launch gate 4, last piece — ADR-151 §2 requires the sign-in code request
-- path to be rate limited **per address and per IP**. Guessing a code was
-- already capped (CODE_MAX_ATTEMPTS); *asking* for one was not, so anyone
-- could trigger unlimited mail to a guessed address.
--
-- Creates the counter table. PURELY ADDITIVE — nothing is altered, nothing is
-- dropped, and an empty table simply means nobody has requested a code yet.
--
-- Both identifiers are stored as SHA-256 digests, never raw: a throttle counts
-- attempts for addresses that may not be users at all, and ADR-154's rule is
-- that accountability records carry ids rather than contact details. Counting
-- works identically on a digest. These rows are a counter, not an audit trail.
--
-- `create_all()` would create this table too, since it only ever creates
-- missing ones — this script exists so the schema change is written down and
-- can be applied to a database whose app has not restarted yet.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0005_login_code_requests.sql

BEGIN;

CREATE TABLE IF NOT EXISTS login_code_requests (
    id           SERIAL PRIMARY KEY,
    address_hash VARCHAR(64) NOT NULL,
    client_hash  VARCHAR(64) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every read is "how many rows for this identifier inside this window", so
-- both indexes are on the identifier and the scan is narrowed by created_at.
CREATE INDEX IF NOT EXISTS ix_login_code_requests_address_hash
    ON login_code_requests (address_hash);
CREATE INDEX IF NOT EXISTS ix_login_code_requests_client_hash
    ON login_code_requests (client_hash);
CREATE INDEX IF NOT EXISTS ix_login_code_requests_created_at
    ON login_code_requests (created_at);

-- Redundant with the primary key, and created only so that a table built by
-- this script is byte-identical to one built by `create_all()` — every model
-- in this codebase declares `index=True` on its id, so SQLAlchemy emits this.
-- Two creation paths that disagree about the schema is the bug this avoids.
CREATE INDEX IF NOT EXISTS ix_login_code_requests_id
    ON login_code_requests (id);

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0005 verification ---'

SELECT
    (SELECT count(*) FROM information_schema.tables
       WHERE table_name = 'login_code_requests')                      AS table_present,
    (SELECT count(*) FROM information_schema.columns
       WHERE table_name = 'login_code_requests')                      AS columns,
    (SELECT count(*) FROM pg_indexes
       WHERE tablename = 'login_code_requests')                       AS indexes,
    (SELECT count(*) FROM login_code_requests)                        AS rows_present;

\echo 'table_present must be 1, columns 4, indexes 5 (4 above + the primary key).'
\echo 'rows_present is 0 on a first run — there is nothing to backfill.'
\echo ''
