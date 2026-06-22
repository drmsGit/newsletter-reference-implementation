---
type: adr
status: accepted
topic:
  - architecture
  - dynamic-content
  - decision-layer
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
  - "[[ADR-021 — Variants Are Human Created Versions]]"
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
enables:
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
---


## Status
Accepted

## Context
Dynamic and personalized content selection can become complex.
If the Builder directly decides personalized content for each recipient or segment, it risks becoming too technical and too hard for non-specialist users.

## Decision
Dynamic content resolution happens outside the Builder.
The Builder defines that a slot is dynamic, selects the layout and may provide constraints such as category, type or allowed content scope.
The actual content decision happens in a Decision Layer or during rendering.

## Consequences

### Positive
- keeps the Builder simple
- separates composition from personalization logic
- supports future AI or rules-based selection
- avoids turning the Builder into a black box content generator
- keeps marketer control over where dynamic content appears

### Negative
- requires a separate decision or rendering component
- previewing dynamic output becomes harder
- governance rules are needed for automated selection

## Notes
AI recommendations inside the Builder are a different concept. They assist composition. They do not replace dynamic resolution at render or decision time.

## Related ADRs

### Depends On

- [[ADR-010 — Newsletter Content Source of Truth]]
- [[ADR-021 — Variants Are Human Created Versions]]
- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]

### Enables

- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
