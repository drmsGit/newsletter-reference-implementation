---
type: adr
status: accepted
topic:
  - architecture
  - provider
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
enables:
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
  - "[[ADR-103 — Provider Events Are Normalized Into Internal Events]]"
  - "[[ADR-104 — Audience Ownership Stays Outside Provider]]"
  - "[[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]]"
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
---


## Status

Accepted

## Context

Newsletter providers offer different functionality.

The reference architecture must remain provider-independent.

## Decision

A provider is treated as a Send and Feedback Adapter.

Provider responsibilities:

- send email
- return delivery feedback
- return engagement feedback

Provider responsibilities do not include:

- CRM ownership
- audience ownership
- content ownership
- automation ownership

## Consequences

### Positive

- provider independence
- cleaner architecture boundaries
- easier migration

### Negative

- feedback normalization required

## Related ADRs

### Depends On

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]

### Enables

- [[ADR-101 — Provider Capabilities Are Explicit]]
- [[ADR-103 — Provider Events Are Normalized Into Internal Events]]
- [[ADR-104 — Audience Ownership Stays Outside Provider]]
- [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
