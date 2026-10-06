-- migrate_0033_module_hidden_fields.sql
--
-- task-290, ADR-187 (decided with the user 2026-10-05/06). A module in a
-- variant carries the fields its manager hid: a JSON list of field names,
-- each one its manifest marks hideable. A layout choice, not content, so it
-- lives on the module — not on the record or the override — survives
-- re-binding the record and copies when the variant is duplicated. Empty for
-- every existing module: nothing was hidden before this.
--
-- Safe to re-run.

BEGIN;
ALTER TABLE module_instances ADD COLUMN IF NOT EXISTS hidden_fields json NOT NULL DEFAULT '[]';
COMMIT;
