---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - ai
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]"
enables:
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
  - "[[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]"
  - "[[ADR-085 — Decision Resolution Should Be Optionally Explainable]]"
---


## Status

Accepted

## Context

AI can improve personalization, but unrestricted AI selection creates governance risks.

## Decision

AI ranks content within a governed candidate set.

The candidate set is created from:

- content metadata
- categories
- category relations
- scoring
- business rules
- engagement signals

AI does not freely select from the complete catalog.

## Consequences

### Positive

- controlled personalization
- better explainability
- reduced risk of unsuitable content
- supports automation without losing governance

### Negative

- candidate set logic must be maintained

## Related ADRs

### Depends On

- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]

### Enables

- [[ADR-082 — AI May Recommend but Not Publish]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
- [[ADR-085 — Decision Resolution Should Be Optionally Explainable]]
