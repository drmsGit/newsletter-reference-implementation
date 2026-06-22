---
type: adr
status: accepted
topic:
  - architecture
  - content
  - governance
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
enables:
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
---


## Status
Accepted

## Context
A Content Catalog can quickly become polluted if every campaign-specific text, temporary idea or one-off content block is stored in it.
Large uncontrolled content repositories make editorial governance, automation and AI-supported recommendations harder.

## Decision
Only reusable content should be stored in the Content Catalog.
A content item can be considered reusable once there is a realistic need to use it more than once.
One-off campaign content belongs to the composition layer as an override or manually configured module content.

## Consequences

### Positive
- keeps the content repository clean
- reduces duplicates
- improves future automation quality
- makes AI recommendations easier to control
- forces conscious reuse decisions before creating new records

### Negative
- editors must decide whether content is reusable before adding it
- one-off content needs another place in the workflow
- some borderline cases require judgment

## Notes
The architecture prioritizes content quality and controllability over content volume. This is especially relevant for automated or AI-generated content, which still requires governance.

## Related ADRs

### Depends On

- [[ADR-010 — Newsletter Content Source of Truth]]

### Enables

- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-082 — AI May Recommend but Not Publish]]
