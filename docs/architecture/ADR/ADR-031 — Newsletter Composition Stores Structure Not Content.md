---
type: adr
status: accepted
topic:
  - architecture
  - composition
  - builder
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-030 — Separate Global and Repeatable Structures]]"
enables:
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-079 — Dynamic Resolution Outside Builder]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
  - "[[ADR-060 — Rendering as Independent Layer]]"
---


## Status
Accepted

## Context
If the Builder were deleted, the Content Catalog would still contain the reusable content, but the system would lose the knowledge of which content was used in which order, layout and campaign context.
This shows that the Builder's core output is not content, but composition.

## Decision
A Newsletter Composition stores the structural assembly of a campaign.
It stores which content reference, module, position, configuration and override belongs to a campaign and variant.
It does not own the source content itself.

## Consequences

### Positive
- creates a clear responsibility for the Builder
- separates content management from newsletter assembly
- supports modular rendering
- keeps content reusable across campaigns
- enables future automation over composition data

### Negative
- rendering depends on resolving external content references
- accidental deletion of composition data loses campaign structure
- composition data needs its own persistence and backup strategy

## Notes
The Builder is the user interface for creating and editing compositions. The architectural object is the composition, not the UI.

## Related ADRs

### Depends On

- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-030 — Separate Global and Repeatable Structures]]

### Enables

- [[ADR-040 — Introduce Override Layer]]
- [[ADR-079 — Dynamic Resolution Outside Builder]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-060 — Rendering as Independent Layer]]
