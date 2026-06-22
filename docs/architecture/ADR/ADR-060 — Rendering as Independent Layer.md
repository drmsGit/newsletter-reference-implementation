---
type: adr
status: accepted
topic:
  - architecture
  - rendering
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
enables:
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
  - "[[ADR-063 — Rendering Parity Over Rendering Implementation]]"
  - "[[ADR-102 — Rendering Prepares Tracking Metadata]]"
---


## Status
Accepted

## Context
The Builder is responsible for composition, not for generating final provider-ready email HTML.
Final email rendering has different requirements than browser preview, especially because email clients require specific HTML structures and compatibility rules.

## Decision
Rendering is an independent architectural layer.
It resolves content references, applies overrides, applies module rendering rules, produces final HTML and prepares snapshots or provider exports.

## Consequences

### Positive
- separates editing from final output generation
- supports provider independence
- enables snapshot generation
- allows email-client-specific rendering rules
- makes rendering testable as its own component

### Negative
- adds another component to maintain
- requires clear contracts between composition and rendering
- preview and final output must be kept visually aligned

## Notes
The Builder may provide previews, but the final sendable output belongs to the Rendering Layer.

## Related ADRs

### Depends On

- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]

### Enables

- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-063 — Rendering Parity Over Rendering Implementation]]
- [[ADR-102 — Rendering Prepares Tracking Metadata]]
