---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - snapshot
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-060 — Rendering as Independent Layer]]"
enables:
  - "[[ADR-062 — Snapshot Stores Final Render State]]"
  - "[[ADR-095 — Use Send Instances for Technical Execution Tracking]]"
---


## Status
Accepted

## Context
Content Catalog entries and module logic may change after a campaign has been sent.
Without snapshots, historical emails could not be reproduced reliably and analytics or support investigations could become inconsistent.

## Decision
Generate immutable render snapshots before sending or at final render time.
A snapshot captures the final resolved render state of a campaign or variant in its delivery context.

## Consequences

### Positive
- enables historical reproducibility
- supports support and audit use cases
- stabilizes analytics
- makes provider exports traceable
- protects sent history from later catalog changes

### Negative
- increases storage requirements
- requires snapshot lifecycle management
- adds responsibility to the rendering pipeline

## Notes
This updates the earlier proposed snapshot ADR to accepted, because reproducible final rendering is foundational for the architecture.

## Related ADRs

### Depends On

- [[ADR-060 — Rendering as Independent Layer]]

### Enables

- [[ADR-062 — Snapshot Stores Final Render State]]
- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
