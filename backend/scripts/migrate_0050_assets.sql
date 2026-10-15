-- migrate_0050_assets.sql
--
-- task-112, [[ADR-197 — Images Are Brand Assets, Served Publicly From an Unguessable Path]]:
-- a brand's image library. Files live in the asset store (storage/assets/
-- or ASSETS_DIR, outside the tracked files); this table is the record.
-- Nothing is ever deleted: hidden_at takes an image out of the picker.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES brands(id),
    token VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    label VARCHAR(200) NOT NULL,
    product_id VARCHAR(100),
    sequence INTEGER NOT NULL,
    media_type VARCHAR(50) NOT NULL,
    size_bytes INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    alt_text VARCHAR(500) NOT NULL DEFAULT '',
    hidden_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_assets_id ON assets (id);
CREATE INDEX IF NOT EXISTS ix_assets_brand_id ON assets (brand_id);
CREATE INDEX IF NOT EXISTS ix_assets_brand_name ON assets (brand_id, name);

COMMIT;
