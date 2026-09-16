-- migrate_0009_audit_log.sql
--
-- [[ADR-153 — Audit and Accountability]], accepted 2026-09-15 and until now
-- entirely unbuilt: there was no audit table anywhere in the codebase, and the
-- only "who" field in the whole system was a free-text `created_by` on content
-- versions, typed into a form.
--
-- This is the FIRST SLICE, not the record. It covers the events ADR-153
-- point 2 says have no home at all — sign-in, role grants and removals, user
-- deactivation — plus the brand-creation and duplication events that prompted
-- building it now. Two parts of the Decision are deliberately NOT here and are
-- named so nobody assumes otherwise:
--
--   * point 4's exports and bulk reads;
--   * point 6's aggregated authentication failures (a row per failed attempt
--     is a write-amplification target an unauthenticated attacker controls).
--
-- PURELY ADDITIVE. One new table, no column touched anywhere else.
--
-- NO FOREIGN KEYS, deliberately. An accountability entry has to outlive what
-- it references — ADR-153 point 5 makes that asymmetry explicit: an entry
-- attributing an action to an operator survives the erasure of any recipient.
-- A foreign key would either block that deletion or cascade it, and both
-- destroy the record the log exists to keep. Actor and subject are a type plus
-- an id, resolved on read and allowed to dangle.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0009_audit_log.sql

BEGIN;

CREATE TABLE IF NOT EXISTS audit_events (
    id           SERIAL PRIMARY KEY,
    actor_type   VARCHAR(50)  NOT NULL,
    actor_id     INTEGER,
    action       VARCHAR(100) NOT NULL,
    subject_type VARCHAR(50),
    subject_id   INTEGER,
    brand_id     INTEGER,
    detail       JSON,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- "What has this operator done", newest first — the screen point 1 exists for.
CREATE INDEX IF NOT EXISTS ix_audit_events_actor_recent
    ON audit_events (actor_type, actor_id, created_at);

-- "What happened to this thing" — the read duplication needs, to answer
-- "was this already copied, and to what".
CREATE INDEX IF NOT EXISTS ix_audit_events_subject
    ON audit_events (subject_type, subject_id, created_at);

-- Single-column indexes matching the model's `index=True` declarations, so a
-- table built by this script is identical to one built by create_all(). Two
-- creation paths that disagree about the schema is the bug migrate_0005 added
-- a redundant index to avoid.
CREATE INDEX IF NOT EXISTS ix_audit_events_id       ON audit_events (id);
CREATE INDEX IF NOT EXISTS ix_audit_events_actor_id ON audit_events (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_action   ON audit_events (action);
CREATE INDEX IF NOT EXISTS ix_audit_events_brand_id ON audit_events (brand_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_created_at ON audit_events (created_at);

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------

\echo ''
\echo '--- migrate_0009 verification ---'

SELECT
    (SELECT count(*) FROM information_schema.tables
      WHERE table_name = 'audit_events')                     AS table_present,
    (SELECT count(*) FROM information_schema.columns
      WHERE table_name = 'audit_events')                     AS columns,
    (SELECT count(*) FROM pg_indexes
      WHERE tablename = 'audit_events')                      AS indexes,
    (SELECT count(*) FROM information_schema.table_constraints
      WHERE table_name = 'audit_events'
        AND constraint_type = 'FOREIGN KEY')                 AS foreign_keys,
    (SELECT count(*) FROM audit_events)                      AS rows_present;

\echo 'table_present 1, columns 9, indexes 8 (7 above + the primary key).'
\echo 'foreign_keys must be 0 — see the header; an entry must outlive its subject.'
\echo 'rows_present is 0 on a first run. There is nothing to backfill: the log'
\echo 'starts now, and inventing entries for actions nobody recorded would be'
\echo 'fabricating exactly the evidence this table exists to hold.'
\echo ''
