---
type: adr
status: accepted
topic:
  - architecture
  - provider
  - audience
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-123 — Audience Ownership Depends on Reuse]]"
enables:
  - "[[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]]"
---


## Status

Accepted

## Context

Many providers offer list and audience management.

This creates dependencies on provider-specific data structures.

## Decision

Audience ownership remains outside the provider.

Providers may store recipient data when necessary.

The architecture must not depend on provider-managed audiences.

## Consequences

### Positive

- audience portability
- easier provider migration
- stronger data ownership

### Negative

- synchronization may be required

## Related ADRs

### Depends On

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-123 — Audience Ownership Depends on Reuse]]

### Enables

- [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]]
