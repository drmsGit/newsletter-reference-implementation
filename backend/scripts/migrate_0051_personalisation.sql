-- migrate_0051_personalisation.sql
--
-- task-365, [[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]]:
-- inline personalisation.
--   * recipients get gender (female, male, diverse or empty), first_name and
--     last_name as real columns; the CRM maps its own values onto them.
--     Existing firstname/lastname attributes (the demo seed's) are copied in.
--   * expression_entries: a brand's dictionary, {{name}} -> cases per language.
--   * brands.expressions_started_at: when the brand's dictionary was first
--     used and the starter entries (storage/expressions.json) were copied in,
--     so deleting every entry never brings the starters back.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

ALTER TABLE recipients ADD COLUMN IF NOT EXISTS gender VARCHAR(20);
ALTER TABLE recipients ADD COLUMN IF NOT EXISTS first_name VARCHAR(255);
ALTER TABLE recipients ADD COLUMN IF NOT EXISTS last_name VARCHAR(255);

UPDATE recipients SET first_name = attributes::jsonb ->> 'firstname'
 WHERE first_name IS NULL AND attributes IS NOT NULL AND attributes::jsonb ? 'firstname';
UPDATE recipients SET last_name = attributes::jsonb ->> 'lastname'
 WHERE last_name IS NULL AND attributes IS NOT NULL AND attributes::jsonb ? 'lastname';

ALTER TABLE brands ADD COLUMN IF NOT EXISTS expressions_started_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS expression_entries (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES brands(id),
    name VARCHAR(64) NOT NULL,
    label VARCHAR(200) NOT NULL,
    languages JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_expression_entries_brand_name UNIQUE (brand_id, name)
);
CREATE INDEX IF NOT EXISTS ix_expression_entries_brand_id ON expression_entries (brand_id);

COMMIT;
