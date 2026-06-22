---
type: adr
status: accepted
topic:
  - architecture
  - provider
  - rendering
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-060 — Rendering as Independent Layer]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
enables:
  - "[[ADR-103 — Provider Events Are Normalized Into Internal Events]]"
---


## Status

Accepted

## Context

Tracking must remain independent from specific providers.

The architecture needs a stable tracking model.

## Decision

Tracking metadata is generated during rendering.

Tracking identifiers may include:

- campaignId
- variantId
- contentId
- sendInstanceId

Providers may extend tracking implementation details.

## Consequences

### Positive

- provider-independent tracking model
- easier event normalization
- stable reporting foundation

### Negative

- rendering becomes responsible for tracking preparation

## Related ADRs

### Depends On

- [[ADR-060 — Rendering as Independent Layer]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]

### Enables

- [[ADR-103 — Provider Events Are Normalized Into Internal Events]]
