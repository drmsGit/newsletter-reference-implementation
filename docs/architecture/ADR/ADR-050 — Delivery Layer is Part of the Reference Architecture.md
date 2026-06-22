---
type: adr
status: accepted
topic:
  - architecture
  - delivery
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-022 — Delivery Type Is Independent From Composition]]"
  - "[[ADR-060 — Rendering as Independent Layer]]"
enables:
  - "[[ADR-051 — Delivery Package Includes More Than HTML]]"
  - "[[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]"
  - "[[ADR-053 — Maintain Minimal Delivery Execution History]]"
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
  - "[[ADR-055 — Separate Delivery Execution from Engagement Events]]"
  - "[[ADR-056 — Engagement Events as Foundation for Automation]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
---


## Status

Accepted

## Context

Many newsletter architectures stop at HTML generation and delegate delivery concerns to an external provider.

This creates provider lock-in and reduces transparency regarding delivery decisions.

## Decision

The reference architecture includes a dedicated Delivery Layer.

The Delivery Layer is responsible for defining:

- audience
- delivery type
- send timing
- variant allocation
- delivery metadata

before handing over execution to a provider.

## Consequences

### Positive

- provider independence
- consistent delivery model
- better observability
- easier automation

### Negative

- additional architectural component
- more implementation effort

## Notes

Delivery execution may still happen in external systems.

The architecture defines delivery behavior independently of the provider.

## Related ADRs

### Depends On

- [[ADR-022 — Delivery Type Is Independent From Composition]]
- [[ADR-060 — Rendering as Independent Layer]]

### Enables

- [[ADR-051 — Delivery Package Includes More Than HTML]]
- [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]
- [[ADR-053 — Maintain Minimal Delivery Execution History]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-056 — Engagement Events as Foundation for Automation]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
