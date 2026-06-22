---
type: adr
status: accepted
topic:
  - architecture
  - overrides
  - rendering
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
enables:
  - "[[ADR-041 — Override Precedence]]"
  - "[[ADR-060 — Rendering as Independent Layer]]"
---


## Status
Accepted

## Context
Catalog content alone is insufficient for editorial newsletter workflows.
Editors often need campaign-specific adjustments, CTA changes, headline changes, temporary adaptations or layout-specific modifications.
Editing the catalog directly for these cases would create unintended global changes and reduce reuse.

## Decision
Introduce an Override Layer.
Overrides are stored separately from catalog content and merged with referenced content during preview or rendering.

## Consequences

### Positive
- enables editorial flexibility
- protects reusable catalog content
- supports layout-specific adaptations
- reduces content duplication
- allows one-off campaign content without polluting the catalog

### Negative
- increases rendering complexity
- requires original-versus-modified detection
- makes preview and usage visibility more important
- overrides can hide later catalog updates

## Notes
This generalizes the existing reference implementation's override approach.

## Related ADRs

### Depends On

- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]

### Enables

- [[ADR-041 — Override Precedence]]
- [[ADR-060 — Rendering as Independent Layer]]
