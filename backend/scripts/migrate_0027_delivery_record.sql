-- migrate_0027_delivery_record.sql
--
-- ADR-183. Every delivery execution records what its recipient got: when it
-- was sent, that recipient's decision-slot picks with a copy of their values,
-- and a hash of the rendered output. With the snapshot's frame this answers
-- "what content did recipient X get in send Y, as of the send date".
--
-- `sent_at` is new because `updated_at` was the only send-time proxy and any
-- later update overwrites it. All three are nullable: an execution that was
-- never sent has none of them, and rows from before this migration are not
-- backfilled — their content was never recorded and cannot be recovered.
--
-- Safe to re-run.

BEGIN;
ALTER TABLE delivery_executions ADD COLUMN IF NOT EXISTS sent_at timestamptz;
ALTER TABLE delivery_executions ADD COLUMN IF NOT EXISTS delivery_record json;
ALTER TABLE delivery_executions ADD COLUMN IF NOT EXISTS artifact_hash varchar(64);
COMMIT;
