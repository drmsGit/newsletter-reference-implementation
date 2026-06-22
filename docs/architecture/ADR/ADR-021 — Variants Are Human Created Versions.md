---
type: adr
status: accepted
topic:
  - architecture
  - campaign
  - variant
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-020 — Campaign Equals Newsletter]]"
enables:
  - "[[ADR-079 — Dynamic Resolution Outside Builder]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
---


## Status
Accepted

## Context
Newsletter content may differ across audiences, branches, tests or personalization rules.
Not every content difference should become a Builder variant.
Automatic personalization can generate many possible outputs and should not turn the Builder into an uncontrolled black box.

## Decision
A variant is a human-created version of a campaign.
Automatic or AI-driven content selection happens inside a variant through dynamic slots and the Decision or Rendering Layer.
Variants are used when a human deliberately creates, reviews and edits a second version of the same campaign concept.

## Consequences

### Positive
- keeps variants editable and understandable
- avoids hidden black-box newsletter generation
- supports A/B testing and branch-specific content versions
- lets marketers adjust known alternatives without developer involvement

### Negative
- can create many variants in complex workflows
- requires clear governance for when to create a variant versus use dynamic content
- dynamic personalization still needs separate architecture

## Notes
A/B test versions are variants. The delivery logic that decides who receives which variant belongs outside the Builder.

## Related ADRs

### Depends On

- [[ADR-020 — Campaign Equals Newsletter]]

### Enables

- [[ADR-079 — Dynamic Resolution Outside Builder]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
