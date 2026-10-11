-- migrate_0044_brand_profiles.sql
--
-- task-350, [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]
-- and its 2026-10-11 addendum (slice 1's final-design pass).
--
-- 1. `brand_profiles`: a brand's looks. Which fields `field_values` holds is
--    declared in `storage/brand_profile.json`, so the values are JSON.
--    Exactly one default per brand (partial unique index).
-- 2. Every existing brand gets its default: "Default", English, marketing, with
--    the unsubscribe wording filled and the legal details left empty — they
--    are the company's to state (addendum point 4).
-- 3. `variants.brand_profile_id`, backfilled with the default of the variant's
--    campaign's brand, and `variants.brand_profile_notice` (empty).
--
-- Nothing is sent differently by this migration: slice 1a stores and edits
-- profiles; using them in the email is task-357.
--
-- SAFE ON EXISTING DATA. Safe to re-run.
--     venv/bin/python scripts/migrate.py --apply

BEGIN;

CREATE TABLE IF NOT EXISTS brand_profiles (
    id           SERIAL PRIMARY KEY,
    brand_id     INTEGER NOT NULL REFERENCES brands(id),
    name         VARCHAR(200) NOT NULL,
    language     VARCHAR(20) NOT NULL DEFAULT 'en',
    kind         VARCHAR(20) NOT NULL DEFAULT 'marketing',
    is_default   BOOLEAN NOT NULL DEFAULT false,
    field_values JSON NOT NULL DEFAULT '{}',
    created_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_brand_profiles_brand_name UNIQUE (brand_id, name),
    CONSTRAINT ck_brand_profiles_kind CHECK (kind IN ('marketing','transactional'))
);
CREATE INDEX IF NOT EXISTS ix_brand_profiles_id ON brand_profiles (id);
CREATE INDEX IF NOT EXISTS ix_brand_profiles_brand_id ON brand_profiles (brand_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_brand_profiles_one_default_per_brand
    ON brand_profiles (brand_id) WHERE is_default = true;

INSERT INTO brand_profiles (brand_id, name, language, kind, is_default, field_values)
SELECT b.id, 'Default', 'en', 'marketing', true, '{"unsubscribe_text": "Unsubscribe"}'
  FROM brands b
 WHERE NOT EXISTS (
       SELECT 1 FROM brand_profiles p WHERE p.brand_id = b.id AND p.is_default);

ALTER TABLE variants ADD COLUMN IF NOT EXISTS brand_profile_id INTEGER REFERENCES brand_profiles(id);
ALTER TABLE variants ADD COLUMN IF NOT EXISTS brand_profile_notice VARCHAR(255);
CREATE INDEX IF NOT EXISTS ix_variants_brand_profile_id ON variants (brand_profile_id);

UPDATE variants v
   SET brand_profile_id = p.id
  FROM campaigns c, brand_profiles p
 WHERE v.campaign_id = c.id
   AND p.brand_id = c.brand_id AND p.is_default
   AND v.brand_profile_id IS NULL;

COMMIT;
