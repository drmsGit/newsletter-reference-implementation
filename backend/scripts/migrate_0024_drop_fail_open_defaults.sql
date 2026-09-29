-- migrate_0024_drop_fail_open_defaults.sql
--
-- task-12, ADR-181 addendum of 2026-09-29. The first full comparison of the
-- development database against a schema built from the models found eight
-- server-side defaults the models did not declare. Migrations had added NOT
-- NULL columns with `DEFAULT x` so existing rows could be backfilled, and the
-- models set their defaults in Python instead — so a database built by the
-- migrations and one built by `create_all` held different schemas.
--
-- The rule the addendum records: **the database never supplies a default the
-- models do not declare.** Five of the eight were harmless and true (counts of
-- 0, booleans) and the models now declare them. These three are dropped
-- instead, because each is a fail-open default an ADR refuses — a raw insert
-- that leaves the column out gets a value nobody chose:
--
--   send_instances.audience_resolution_mode  DEFAULT 'freeze'
--     The mode ADR-176 point 4 removed. The model has defaulted to 'rerun'
--     since that point was implemented; the database still said 'freeze'.
--
--   delivery_executions.channel  DEFAULT 'email'
--     The channel decides who may be contacted, not merely how — the default
--     ADR-176's 2026-09-27 addendum removed from resolve_audience, one layer
--     further down.
--
--   delivery_executions.purpose  DEFAULT 'marketing'
--     Consent is keyed by purpose (ADR-163); a purpose nobody stated is a
--     guess about which consent applies.
--
-- The ORM always writes all three, so no application path changes. What
-- changes is that an INSERT naming none of them now fails on NOT NULL instead
-- of silently choosing — which is the point.
--
-- The Python-side `default="email"` / `default="marketing"` on
-- DeliveryExecutionDB are the same class and are NOT changed here; that is
-- task-42's scope.
--
-- Safe to re-run: DROP DEFAULT on a column without one is a no-op.

BEGIN;

ALTER TABLE send_instances ALTER COLUMN audience_resolution_mode DROP DEFAULT;
ALTER TABLE delivery_executions ALTER COLUMN channel DROP DEFAULT;
ALTER TABLE delivery_executions ALTER COLUMN purpose DROP DEFAULT;

COMMIT;
