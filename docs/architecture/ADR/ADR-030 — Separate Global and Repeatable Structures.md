---
type: adr
status: accepted
topic:
  - architecture
  - composition
  - data-model
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
enables:
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
  - "[[ADR-060 — Rendering as Independent Layer]]"
---


## Status
Accepted

## Context
Newsletter content contains global campaign-level information and repeatable modular content.
Storing both in one flat structure makes sorting, rendering, variants and modular workflows harder.

## Decision
Separate global newsletter structures from repeatable content structures.
Global structures contain metadata such as subject, preheader and header-level information.
Repeatable structures contain modular rows or blocks with position, module type, content reference, configuration and overrides.

## Consequences

### Positive
- enables modular rendering
- simplifies row or block ordering
- supports variants
- keeps campaign metadata separate from repeated content blocks
- makes export and snapshot generation easier

### Negative
- loading and saving become more complex
- synchronization between global and repeatable structures is required
- the UI must handle both levels consistently

## Notes
This generalizes the original reference implementation decision to separate header and row storage.

## Related ADRs

### Enables

- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]
- [[ADR-060 — Rendering as Independent Layer]]
