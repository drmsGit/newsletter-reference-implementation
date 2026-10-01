-- migrate_0026_login_code_kdf.sql
--
-- task-35. The six-digit login code was stored as bare SHA-256 — 10^6 values,
-- precomputable once by anyone who can read the table, and colliding across
-- users with the same code. It is now `scrypt$<salt>$<hash>` (~104 characters),
-- so the column widens from 64 to 128.
--
-- No data is converted, deliberately. A code is valid for ten minutes, and the
-- verify path treats a row without the scrypt prefix as never matching, so a
-- code issued before this migration simply fails and the person asks for
-- another. Rewriting live codes would need the codes themselves, which are not
-- stored — that is the point.
--
-- The other uses of the same SHA-256 helper (session tokens, machine secrets,
-- rate-limit identifiers) are high-entropy and untouched.
--
-- Safe to re-run.

BEGIN;
ALTER TABLE login_codes ALTER COLUMN code_hash TYPE varchar(128);
COMMIT;
