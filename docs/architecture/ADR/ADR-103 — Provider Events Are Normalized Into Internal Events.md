---
type: adr
status: accepted
topic:
  - architecture
  - provider
  - analytics
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-102 — Rendering Prepares Tracking Metadata]]"
enables:
  - "[[ADR-055 — Separate Delivery Execution from Engagement Events]]"
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
---


## Status

Accepted

## Context

Providers expose different event models.

Direct usage would create provider lock-in.

## Decision

Provider-specific events must be transformed into a provider-independent internal event model.

Examples:

- open
- click
- bounce
- complaint
- unsubscribe

## Consequences

### Positive

- provider independence
- reusable analytics
- reusable automation logic

### Negative

- event transformation layer required

## Related ADRs

### Depends On

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-102 — Rendering Prepares Tracking Metadata]]

### Enables

- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
