---
type: adr
status: accepted
topic:
  - architecture
  - delivery
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-123 — Audience Ownership Depends on Reuse]]"
---


## Status

Accepted

## Context

Different organizations have different levels of maturity.

Some use audience systems.

Others only have exported recipient lists.

## Decision

The architecture supports multiple audience resolution approaches:

- audience references
- audience queries
- explicit recipient lists

The simplest suitable solution should be preferred.

## Consequences

### Positive

- flexible adoption
- lower entry barrier
- compatible with different environments

### Negative

- more implementation scenarios

## Notes

No single audience strategy is enforced.

## Related ADRs

### Depends On

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-123 — Audience Ownership Depends on Reuse]]
