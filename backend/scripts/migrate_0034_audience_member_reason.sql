-- migrate_0034_audience_member_reason.sql
--
-- task-295, decided with the user 2026-10-06 (task-293; Audience Write
-- Surface final design pass, decision 5): a person added to an audience by
-- hand carries an optional reason and who added them (closes task-217).
-- Existing rows keep both empty: nobody recorded why they were added.
--
-- Safe to re-run.

BEGIN;
ALTER TABLE audience_group_members ADD COLUMN IF NOT EXISTS reason text;
ALTER TABLE audience_group_members ADD COLUMN IF NOT EXISTS added_by varchar(255);
COMMIT;
