-- migrate_0015_integrations.sql
--
-- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], stage 2:
-- the machine principal and its credentials. Nothing is guarded yet — the
-- routers are wired in stage 3 — so this migration adds capability and changes
-- no existing behaviour.
--
-- **Three tables and not two.** The integration is separate from its
-- credentials because the integration is the durable audit actor (point 3):
-- keys are issued, rotated and revoked beneath it, and history stays
-- continuous across a rotation. A credential-as-actor model answers "who
-- triggered this send" with a row pointing at something revoked six months
-- ago.
--
-- **Grants are permissions, not roles** (point 7 and its 2026-09-18 addendum).
-- A role names a job and an integration does not have one — it has the list of
-- calls it makes. `brand_id` is NOT NULL exactly as `role_assignments.brand_id`
-- is, so a platform-level permission is checked without a brand filter for a
-- machine the same way it is for a person.

CREATE TABLE IF NOT EXISTS integrations (
    id                   SERIAL PRIMARY KEY,
    name                 VARCHAR(200) NOT NULL,
    description          VARCHAR(500),
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    -- ADR-166 point 5: the most destructive capability in the system is not
    -- the one that defaults open. A machine-triggered send lands in the
    -- approval surface unless somebody deliberately switched this on.
    may_send_unattended  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Who set it up, for the access list. NOT ownership: point 4 makes a
    -- credential independent of its issuer, so deactivating this user revokes
    -- nothing. That hole is booked in the ADR's Negative section.
    created_by_user_id   INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS integration_credentials (
    id              SERIAL PRIMARY KEY,
    integration_id  INTEGER NOT NULL REFERENCES integrations(id),
    -- The public half. Safe in a log line: it names the caller and proves
    -- nothing. Unique so a failing request can be attributed and counted
    -- without the secret being resolved first (point 1).
    key_id          VARCHAR(64) NOT NULL UNIQUE,
    -- Hashed, never reversible ciphertext. ADR-151 §2 plus ADR-152's Notes.
    secret_hash     VARCHAR(64) NOT NULL,
    label           VARCHAR(200),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Written on success only. A failed attempt proves nothing about who holds
    -- the key, so counting it here would let an outsider write to this row.
    last_used_at    TIMESTAMPTZ,
    -- Immediate, not effective at next expiry (point 3, inheriting ADR-151 §3).
    revoked_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_integration_credentials_integration_id
    ON integration_credentials (integration_id);
CREATE INDEX IF NOT EXISTS ix_integration_credentials_key_id
    ON integration_credentials (key_id);

CREATE TABLE IF NOT EXISTS integration_grants (
    id              SERIAL PRIMARY KEY,
    integration_id  INTEGER NOT NULL REFERENCES integrations(id),
    permission      VARCHAR(100) NOT NULL,
    brand_id        INTEGER NOT NULL REFERENCES brands(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_integration_permission_brand
        UNIQUE (integration_id, permission, brand_id)
);

CREATE INDEX IF NOT EXISTS ix_integration_grants_integration_id
    ON integration_grants (integration_id);
CREATE INDEX IF NOT EXISTS ix_integration_grants_brand_id
    ON integration_grants (brand_id);
