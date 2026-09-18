-- migrate_0011_variant_header_module.sql
--
-- [[ADR-162 — Channel Rendering and Artifacts]] point 1: "The variant holds no
-- channel fields at all. Subject and preheader become module fields, declared
-- in a manifest." A `header` module for email at position 0, exactly as push's
-- single module declares title / body / image / link.
--
-- This is the EXPAND half. It creates the header modules and copies the values
-- across; `variants.subject` and `variants.preheader` are left in place and
-- still read as a fallback, so a half-applied deployment cannot send mail with
-- no subject line. The columns are dropped by a later contract migration, once
-- nothing reads them.
--
-- Position 0, not 1. `create_module_for_variant` appends at max+1 and existing
-- modules therefore start at 1, so 0 is free on every variant and this needs no
-- renumbering — which matters because `(variant_id, position)` is unique and
-- shifting every row would be a far bigger change than adding one.
--
-- Only variants that HAVE envelope copy get a module. A variant with neither a
-- subject nor a preheader gets nothing: an empty header module would be a row
-- asserting that somebody wrote envelope copy, and nobody did.
--
-- Only EMAIL variants. A push variant has no subject by construction, and the
-- header manifest declares channel "email", so a header module on a push
-- variant would be refused by the registry's own misfiling assertion.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0011_variant_header_module.sql

BEGIN;

INSERT INTO module_instances (variant_id, module_type, position, module_data)
SELECT
    v.id,
    'header',
    0,
    -- Only the keys that have a value. A module_data of {"subject": null}
    -- would read as "authored and left empty", which is a different claim.
    (
        SELECT jsonb_object_agg(k, val)
          FROM (
              SELECT 'subject'::text AS k, v.subject AS val WHERE v.subject IS NOT NULL
              UNION ALL
              SELECT 'preheader'::text, v.preheader WHERE v.preheader IS NOT NULL
          ) AS kv
    )::json
FROM variants v
WHERE v.channel = 'email'
  AND (v.subject IS NOT NULL OR v.preheader IS NOT NULL)
  AND NOT EXISTS (
      SELECT 1 FROM module_instances m
       WHERE m.variant_id = v.id AND m.module_type = 'header'
  );

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------
-- Every email variant with envelope copy should now have exactly one header
-- module, and its data should match the columns:
--
--   SELECT v.id, v.subject, v.preheader, m.position, m.module_data
--     FROM variants v
--     LEFT JOIN module_instances m
--       ON m.variant_id = v.id AND m.module_type = 'header'
--    WHERE v.subject IS NOT NULL OR v.preheader IS NOT NULL
--    ORDER BY v.id;
--
-- Expect zero rows (no variant with copy and no module):
--
--   SELECT v.id FROM variants v
--    WHERE v.channel = 'email'
--      AND (v.subject IS NOT NULL OR v.preheader IS NOT NULL)
--      AND NOT EXISTS (SELECT 1 FROM module_instances m
--                       WHERE m.variant_id = v.id AND m.module_type = 'header');
