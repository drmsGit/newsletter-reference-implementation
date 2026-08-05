---
type: moc
topic:
  - architecture
  - security-architecture
  - privacy
created: 2026-08-02
modified: 2026-08-02
---

# MOC - Security Architecture

Who may act, how they prove it, what the system remembers about it, and what happens when a person asks to be forgotten. Designed in the 2026-08-02 Security Chapter interview; **all five ADRs are proposed, none implemented.**

## ADRs

- [[ADR-150 — Tenancy and Access Model]] — single-tenant, roles, brands as scope
- [[ADR-151 — Authentication and Sessions]] — passwordless code, sessions, passkeys as an optional layer
- [[ADR-152 — Secret and Credential Handling]] — environment as interface, write-only credentials
- [[ADR-153 — Audit and Accountability]] — append-only actor-attributed log
- [[ADR-154 — Erasure and Retention]] — identity/activity separation, full erasure as default

## Foundational dependencies

- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]] — privacy operations as architecture; ADR-154 is operational detail beneath it
- [[ADR-054 — Use Internal Recipient Identifiers]] — the convention that makes erasure tractable
- [[ADR-122 — Minimal Consent Model Required]] — a **proposed amendment** splits consent by *purpose* (marketing opt-in vs transactional basis); recorded in the `playbook-strategy.md` Decision Log, not yet written

## Open

- **Step-up authentication** for destructive actions (ADR-151)
- **Retention periods** — company determination; the architecture supplies the prune mechanism (ADR-154)
- **Breach response** (Art. 33/34) — the adopter's process; architecture owes detection and scoping
- **Machine authentication** for inbound API callers — a separate concern and a Mode B prerequisite, tracked in `docs/backlog.md`

## Related MOCs

- [[MOC - Newsletter Architecture]]
- [[MOC - Data Foundation]]
- [[MOC - AI Architecture]]
