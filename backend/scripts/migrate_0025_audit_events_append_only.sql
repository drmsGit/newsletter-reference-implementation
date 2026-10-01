-- migrate_0025_audit_events_append_only.sql
--
-- task-25. `audit_events` is append-only by design — no field invites an
-- update and the service exposes only `record()` — but that is discipline, and
-- it stops holding the day a mutable column is added. This makes the database
-- refuse an UPDATE.
--
-- **A trigger, not REVOKE UPDATE.** The REVOKE was measured first and does
-- nothing in this deployment: the application role is a superuser, and a
-- superuser bypasses privilege checks — an UPDATE succeeded straight after
-- revoking it. A trigger fires for every role.
--
-- The same function and trigger are created by `create_all` (an after_create
-- listener on AuditEventDB), so a test database and a migrated one agree; the
-- schema comparison now checks triggers.
--
-- UPDATE only. DELETE stays possible: test cleanup removes audit rows, and
-- whether an erasure request may remove an entry is ADR-153 point 5's question.
--
-- Safe to re-run.

BEGIN;

CREATE OR REPLACE FUNCTION audit_events_refuse_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only: an entry cannot be updated (ADR-153)';
END
$$;

DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
CREATE TRIGGER audit_events_append_only
BEFORE UPDATE ON audit_events
FOR EACH ROW EXECUTE FUNCTION audit_events_refuse_update();

COMMIT;
