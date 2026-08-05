---
type: adr
status: proposed
topic:
  - architecture
  - security
  - operations
created: 2026-08-02
modified: 2026-08-02
source:
  - "Security Chapter design interview, Part 2 (playbook-strategy.md Decision Log, 2026-08-02)"
depends_on:
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
---

## Status
Proposed

## Context

The platform now holds several live credentials: a send-provider API key ([[ADR-100 — Provider Layer as Send and Feedback Adapter]]), an inbound webhook signing secret, and a model API key ([[ADR-144 — AI Data and Model Governance]]). More will follow as adapters are added.

Today they are read from the process environment, populated at startup from a gitignored `backend/.env`. That is a reasonable *development* arrangement and not a production one, and the playbook currently has no answer to give an adopter.

Two things sharpen the question beyond ordinary hygiene. [[ADR-150 — Tenancy and Access Model]] put **external agency staff in the Admin role**, so the people configuring providers may not work for the company whose credentials those are. And the **Cyber Resilience Act** applies to products with digital elements placed on the EU market commercially — which the paid starter package plausibly is — bringing security-by-design and documentation obligations that a reviewer will look for by name.

## Decision

**1. The environment is the interface; deployment decides how it is populated.**
The application reads credentials from the process environment and never learns where a value came from. No secrets in code, in the database, or in any file the application itself manages. This keeps the application ignorant of, and therefore compatible with, every way an adopter might choose to inject secrets.

**2. `.env` is development-only, and the documentation says so plainly.**
Production populates the environment through the deployment mechanism already in use — Docker/Compose secrets, systemd credentials, or Kubernetes secrets. A managed secret store (Vault, Infisical, Scaleway Secret Manager) is the **documented seam** for companies that want one, not a dependency we take.

**3. Rotation is "update the environment, restart."**
Nothing is cached beyond process lifetime, so no key is held anywhere the restart does not clear. This is true of the current implementation by accident; the decision makes it a property to preserve rather than a coincidence to break later.

**4. Credentials are write-only in the user interface.**
An Admin may set or replace a credential and may see **that one is configured** — never its value. The API must not return a stored credential under any circumstance, including to the Admin who set it.

This follows directly from ADR-150's agency-operator decision. Without it, "the agency helps operate the system" quietly also means the agency can read out the company's sending and model credentials, with the audit trail recording only that somebody opened a settings page. Write-only turns credential access into credential *replacement*, which is visible, attributable and revocable.

**5. Startup reports what it loaded, by name and never by value.**
A credential that is present but not loaded is invisible, and the resulting failure looks like a bug in whatever needed it. Startup logs which variables were found, which were ignored and why — names only.

## Consequences

### Positive
- No new infrastructure dependency; the same code runs on a single Hetzner box and in a cluster.
- Adopters use whatever secret mechanism they already operate, rather than adopting ours.
- An external operator can keep the system running without ever being able to exfiltrate the credentials they operate it with.
- Satisfies the "how are secrets handled" question that ISO 27001 and CRA reviewers ask, with a findable answer.
- Rotation has a defined, testable procedure rather than being folklore.

### Negative
- Rotation requires a restart, so key rotation is a small planned outage rather than a live operation. Accepted as the cost of never caching a secret.
- Write-only credentials mean a lost key is unrecoverable from the platform — the company must retrieve it from the provider or its own secret store. This is the intended trade, but it will surface as a support question.
- The application cannot verify that a production deployment actually stopped using `.env`; the guarantee is documentation and review, not enforcement.

## Notes

- Deliberately **not** chosen: encrypting secrets at rest in the database. It moves the problem rather than solving it — the decryption key still has to live somewhere outside the database — while adding a schema, a migration path and a false sense of security.
- The startup reporting in point 5 is already implemented in `main.py` (loaded / ignored-empty / invalid-name, names only) as of 2026-08-02; the rest of this ADR is documentation and a UI constraint rather than new machinery.
- **Machine credentials issued *by* the platform** to inbound API callers are a separate concern, tracked in `docs/backlog.md` as a Mode B prerequisite. This ADR covers credentials the platform *holds*, not credentials it *issues*.

## Related ADRs

### Depends On
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-144 — AI Data and Model Governance]]
