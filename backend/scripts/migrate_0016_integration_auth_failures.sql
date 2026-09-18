-- migrate_0016_integration_auth_failures.sql
--
-- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 3,
-- inheriting [[ADR-153 — Audit and Accountability]] §6: failed authentication
-- is **aggregated**, not recorded one attempt per row.
--
-- The reason is written into ADR-153 and applies here word for word: an
-- unauthenticated attacker can generate failures at will. These routes are
-- reachable by exactly that attacker, so a row-per-attempt table would hand
-- whoever can reach the port an unbounded write primitive — an accountability
-- record turned into a denial-of-service surface.
--
-- One row per (claimed key, client, hour), with a counter.
--
-- **The claimed key is stored readable, the client is hashed.** That is not an
-- inconsistency. ADR-154 §3 holds accountability records to internal
-- identifiers rather than contact details, and a key id is an internal
-- identifier that ADR-166 point 1 makes public by design — it is the half that
-- identifies without proving. Storing it readable is what makes the aggregate
-- worth having, because "someone is hammering n8n's key" is the finding. The
-- client identifier is a network address, which is not ours, so it is hashed.

CREATE TABLE IF NOT EXISTS integration_auth_failures (
    id            SERIAL PRIMARY KEY,
    -- Attacker-controlled input from a header. Truncated by the application
    -- to this width before it arrives: an unbounded string has no business
    -- deciding a row's size.
    key_id        VARCHAR(64) NOT NULL,
    client_hash   VARCHAR(64) NOT NULL,
    window_start  TIMESTAMPTZ NOT NULL,
    attempts      INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT uq_integration_auth_failure_window
        UNIQUE (key_id, client_hash, window_start)
);

CREATE INDEX IF NOT EXISTS ix_integration_auth_failures_key_id
    ON integration_auth_failures (key_id);
CREATE INDEX IF NOT EXISTS ix_integration_auth_failures_window_start
    ON integration_auth_failures (window_start);
