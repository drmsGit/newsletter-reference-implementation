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
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
enables:
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
---


## Status

Accepted

## Context

Providers support different feature sets.

Not all providers offer the same delivery and tracking capabilities.

## Decision

Provider capabilities must be explicitly defined.

Core capabilities:

- send
- delivery status
- bounce feedback
- complaint feedback

Optional capabilities:

- click tracking
- open tracking
- audience synchronization
- provider-specific features

## Consequences

### Positive

- transparent integrations
- easier provider comparisons
- avoids hidden dependencies

### Negative

- capability mapping required

## Related ADRs

### Depends On

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]

### Enables

- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
