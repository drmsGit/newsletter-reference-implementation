---
type: adr
status: accepted
topic:
  - architecture
  - campaign
  - delivery
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-020 — Campaign Equals Newsletter]]"
enables:
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]"
---


## Status
Accepted

## Context
The same newsletter composition can be used in different delivery contexts.
Single sends and recurring or automated sends have different operational behavior, but the composition itself does not need to be modeled differently.

## Decision
Delivery type is separated from newsletter composition.
Single send, recurring and triggered delivery are Delivery Definitions, not different types of newsletter composition.

## Consequences

### Positive
- keeps composition focused on content and structure
- allows the same composition model for single and automated sends
- enables future provider abstraction
- makes delivery behavior easier to change independently

### Negative
- delivery metadata still needs to be available for operations and content usage views
- some provider systems may mix composition and delivery concepts

## Notes
Content usage views may still display whether a campaign is used in single or automated delivery, because catalog changes are more relevant for active recurring sends.

## Related ADRs

### Depends On

- [[ADR-020 — Campaign Equals Newsletter]]

### Enables

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]
