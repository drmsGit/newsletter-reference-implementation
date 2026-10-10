-- migrate_0043_envelope_module_rows.sql
--
-- task-349, [[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]]
-- point 6: the email module holding the subject and preheader is renamed from
-- `header` to `envelope`, freeing `header` for the visible logo header.
--
-- LIVE ROWS ONLY. Module rows in variants take the new name. Snapshots are
-- deliberately NOT touched: a frozen frame keeps saying `header`, because
-- `module_html` writes the type into the HTML, and rewriting it would change
-- what every sent email reconstructs to (ADR-183). Version-1 frames are read
-- with the old name instead (`rendering/frame.py`, `lookup_type`).
--
-- Only the email channel has a `header` module today, so the channel filter is
-- belt and braces. Safe to re-run.

BEGIN;

UPDATE module_instances
   SET module_type = 'envelope'
 WHERE module_type = 'header'
   AND variant_id IN (SELECT id FROM variants WHERE channel = 'email');

COMMIT;
