---
type: adr
status: accepted
topic:
  - architecture
  - privacy
  - delivery
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-121 — Minimal Recipient Model]]"
enables:
  - "[[ADR-053 — Maintain Minimal Delivery Execution History]]"
---


## Status

Accepted

## Context

The newsletter architecture should minimize storage of personal data.

CRM and delivery providers already maintain email addresses.

## Decision

Internal processing should primarily use recipient identifiers.

Email addresses should remain in CRM and provider systems whenever possible.

## Consequences

### Positive

- reduced privacy exposure
- cleaner system boundaries
- safer AI processing

### Negative

- additional identifier mapping required

## Related ADRs

### Depends On

- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-121 — Minimal Recipient Model]]

### Enables

- [[ADR-053 — Maintain Minimal Delivery Execution History]]
