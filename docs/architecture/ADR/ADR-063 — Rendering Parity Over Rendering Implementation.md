---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - preview
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-060 — Rendering as Independent Layer]]"
---


## Status
Accepted

## Context
Preview rendering, final rendering and snapshot rendering serve different technical contexts.
The Builder preview may use browser-friendly structures, while final email HTML may require nested tables and email-client-specific markup.

## Decision
Require output parity, not necessarily implementation parity.
Preview, final rendering and snapshots should represent the same intended newsletter output.
They may use different technical render implementations if necessary.

## Consequences

### Positive
- allows technical flexibility
- avoids forcing email-client HTML into every UI preview
- keeps final rendering optimized for email clients
- keeps snapshot generation focused on historical stability

### Negative
- differences between preview and final output must be tested carefully
- module changes may need validation across multiple render contexts
- visual parity can be harder than shared implementation

## Notes
Where shared rendering logic is practical, it should be reused. But the architectural requirement is parity of output, not identical code paths.

## Related ADRs

### Depends On

- [[ADR-060 — Rendering as Independent Layer]]
