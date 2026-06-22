---
type: adr
status: accepted
topic:
  - architecture
  - provider
  - deliverability
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
enables:
  - "[[ADR-122 — Minimal Consent Model Required]]"
---


## Status

Accepted

## Context

Bounce and complaint data are required to maintain list quality and protect sender reputation.

## Decision

Every production-ready provider integration must support:

- bounce feedback
- complaint feedback

Open and click tracking are useful but secondary.

## Consequences

### Positive

- better deliverability
- reputation protection
- cleaner audience management

### Negative

- some providers may not qualify

## Related ADRs

### Depends On

- [[ADR-101 — Provider Capabilities Are Explicit]]

### Enables

- [[ADR-122 — Minimal Consent Model Required]]
