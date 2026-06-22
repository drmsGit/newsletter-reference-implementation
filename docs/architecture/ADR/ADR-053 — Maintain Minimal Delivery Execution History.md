---
type: adr
status: accepted
topic:
  - architecture
  - delivery
  - analytics
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
enables:
  - "[[ADR-055 — Separate Delivery Execution from Engagement Events]]"
  - "[[ADR-095 — Use Send Instances for Technical Execution Tracking]]"
---


## Status

Accepted

## Context

Provider data alone does not provide sufficient data ownership.

Future automation and AI features require a local execution history.

## Decision

The architecture stores a minimal delivery execution history.

Examples:

- campaignId
- variantId
- snapshotId
- recipientId
- contentIds
- sentAt
- providerMessageId

## Consequences

### Positive

- data ownership
- provider independence
- future automation support

### Negative

- additional storage requirements

## Related ADRs

### Depends On

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-054 — Use Internal Recipient Identifiers]]

### Enables

- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
