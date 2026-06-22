---
type: adr
status: accepted
topic:
  - architecture
  - content
  - composition
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
enables:
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
---


## Status
Accepted

## Context
A newsletter may use reusable content from the Content Catalog.
If content is copied into the newsletter at selection time, later catalog updates will not reach active recurring campaigns.
If content is always resolved by reference, centrally maintained content can remain current.

## Decision
Newsletter compositions store references to content records instead of copying the full content into the builder state.
The effective content is resolved during preview or rendering by combining the referenced content with optional overrides.

## Consequences

### Positive
- enables central maintenance of recurring newsletters
- reduces content duplication
- keeps builder data smaller
- makes content usage traceable
- supports the Content Catalog as source of truth

### Negative
- requires reliable content resolution during preview and rendering
- changes in catalog content can affect active campaigns
- usage overview and override visibility become important

## Notes
For sent single campaigns, later catalog updates are usually less relevant because the email is already in the past. For recurring campaigns, central updates are a major benefit. A usage overview should show where a record is used and whether it is used in original or overridden form.

## Related ADRs

### Depends On

- [[ADR-010 — Newsletter Content Source of Truth]]

### Enables

- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
