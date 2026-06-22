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
  - "[[ADR-053 — Maintain Minimal Delivery Execution History]]"
---


## Status

Accepted

## Context

Provider migration should not require rebuilding the architecture.

## Decision

Architecture-critical information must be stored independently from providers.

Examples:

- campaignId
- variantId
- snapshotId
- sendInstanceId
- recipientId
- engagement events

Provider-specific identifiers may be stored as references.

## Consequences

### Positive

- provider independence
- easier migration
- stronger data ownership

### Negative

- additional storage required

## Related ADRs

### Depends On

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-053 — Maintain Minimal Delivery Execution History]]
