-- migrate_0041_unsubscribe_token.sql
--
-- task-56, decided with the user 2026-10-09 (ADR-191 point 2): every
-- delivered message carries an unsubscribe link holding a random token stored
-- with its delivery execution. The message already knows the person, brand,
-- channel and purpose, so the token is the whole credential; nothing is
-- signed, so no missing or rotated secret can break a link already sent.
--
-- Nullable: executions created before this migration, and executions not yet
-- sent, have none. Unique, and indexed by the same unique index the model
-- declares, because the unsubscribe route looks a message up by its token.
--
-- Safe to re-run.

ALTER TABLE delivery_executions ADD COLUMN IF NOT EXISTS unsubscribe_token VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS ix_delivery_executions_unsubscribe_token
    ON delivery_executions (unsubscribe_token);
