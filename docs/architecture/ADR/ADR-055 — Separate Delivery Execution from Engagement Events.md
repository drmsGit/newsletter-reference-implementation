---
type: adr
status: accepted
topic:
  - architecture
  - analytics
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-053 — Maintain Minimal Delivery Execution History]]"
enables:
  - "[[ADR-056 — Engagement Events as Foundation for Automation]]"
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
---


## Status

Accepted

## Context

Delivery records and engagement events have different characteristics.

Delivery records are limited in volume.

Engagement events may be generated in large quantities.

## Decision

Delivery execution and engagement events are modeled separately.

## Consequences

### Positive

- better scalability
- better performance
- cleaner architecture

### Negative

- additional relationships between models

## Related ADRs

### Depends On

- [[ADR-053 — Maintain Minimal Delivery Execution History]]

### Enables

- [[ADR-056 — Engagement Events as Foundation for Automation]]
- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
