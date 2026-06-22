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
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
enables:
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
---


## Status

Accepted

## Context

Sending an email requires more than rendered HTML.

Additional delivery metadata is required by most providers.

## Decision

A delivery package contains:

- rendered HTML
- subject
- preheader
- campaignId
- variantId
- snapshotId
- delivery metadata
- audience information

## Consequences

### Positive

- provider abstraction
- consistent exports
- easier provider migration

### Negative

- larger delivery model

## Related ADRs

### Depends On

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-061 — Snapshot Based Final Rendering]]

### Enables

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
