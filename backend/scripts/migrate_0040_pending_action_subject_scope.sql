-- migrate_0040_pending_action_subject_scope.sql
--
-- task-206, decided with the user 2026-10-08 (ADR-142 addendum of that date):
-- an action may declare a scope inside its subject, and one request is open
-- per subject AND scope. For the content-readiness hold the scope is the
-- channel, so an agency asking for email and push on one record holds two
-- requests rather than having the second refused as already waiting.
--
-- Empty string, not NULL, for every action that declares no scope: a unique
-- index never sees two NULLs as equal, so NULL would quietly drop the
-- one-open-request rule for every existing action. Existing rows get ''.
--
-- Safe to re-run.

ALTER TABLE pending_actions ADD COLUMN IF NOT EXISTS subject_scope VARCHAR(64) NOT NULL DEFAULT '';

DROP INDEX IF EXISTS ux_pending_actions_one_open_per_subject;
CREATE UNIQUE INDEX ux_pending_actions_one_open_per_subject
    ON pending_actions (action_key, subject_type, subject_id, subject_scope)
    WHERE status IN ('pending', 'executing');
