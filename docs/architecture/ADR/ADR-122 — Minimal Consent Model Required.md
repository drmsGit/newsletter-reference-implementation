---
type: adr
status: accepted
topic:
  - architecture
  - crm
  - consent
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
enables:
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
---


## Status

Accepted

## Context

Consent management is not a core responsibility of the newsletter architecture.

However, delivery decisions depend on consent information.

Transactional and marketing communication may require different consent handling.

## Decision

The architecture requires a minimal consent model.

At minimum, the system must distinguish between:

- marketing communication
- transactional communication

Only recipients eligible for the selected communication type may enter delivery processes.

## Consequences

### Positive

- safer communication handling
- compatible with different consent solutions
- supports transactional messaging

### Negative

- consent mapping required during integrations

## Related ADRs

### Depends On

- [[ADR-120 — CRM as Customer Source of Truth]]

### Enables

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
