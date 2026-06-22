---
type: adr
status: accepted
topic:
  - architecture
  - crm
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
enables:
  - "[[ADR-121 — Minimal Recipient Model]]"
  - "[[ADR-122 — Minimal Consent Model Required]]"
  - "[[ADR-123 — Audience Ownership Depends on Reuse]]"
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
---


## Status

Accepted

## Context

The newsletter architecture requires a reliable source for customer and recipient information.

Without a clear source of truth, data duplication, inconsistent segmentation and personalization problems occur.

## Decision

The CRM acts as the Customer Source of Truth.

The CRM owns:

- recipient identifiers
- email addresses
- consent information
- customer master data
- language and country information
- manually maintained segments
- relevant purchase information
- relevant service information

## Consequences

### Positive

- clear ownership
- reduced duplication
- easier provider migration
- cleaner integrations

### Negative

- CRM quality directly impacts newsletter quality

## Related ADRs

### Enables

- [[ADR-121 — Minimal Recipient Model]]
- [[ADR-122 — Minimal Consent Model Required]]
- [[ADR-123 — Audience Ownership Depends on Reuse]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
