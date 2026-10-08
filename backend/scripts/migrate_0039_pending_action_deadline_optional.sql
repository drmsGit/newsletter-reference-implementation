-- migrate_0039_pending_action_deadline_optional.sql
--
-- task-210 (ADR-142 §4, addendum 2026-09-24; Manager Workflow interview Q1.7):
-- the deadline belongs to the action type, and an action type may have none —
-- "is this copy good" does not go stale the way "send the morning campaign"
-- does. A held action with no deadline never expires: every reader treats an
-- empty expires_at as "never", not as "already". Existing rows all carry one.
--
-- Safe to re-run.

ALTER TABLE pending_actions ALTER COLUMN expires_at DROP NOT NULL;
