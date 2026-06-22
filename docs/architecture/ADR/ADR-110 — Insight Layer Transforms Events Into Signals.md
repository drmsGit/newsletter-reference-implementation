---
type: adr
status: accepted
topic:
  - architecture
  - insight
  - analytics
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-055 — Separate Delivery Execution from Engagement Events]]"
  - "[[ADR-103 — Provider Events Are Normalized Into Internal Events]]"
enables:
  - "[[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]"
  - "[[ADR-112 — Signals Use Time-Based Decay]]"
  - "[[ADR-113 — Separate Operational and Historical Signals]]"
  - "[[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]"
---


## Status

Accepted

## Context

Raw engagement events are not suitable for direct decision-making.

The architecture needs reusable decision inputs.

## Decision

The Insight Layer transforms engagement events into reusable signals.

Examples:

- recipient signals
- content signals
- composition signals
- audience signals

The Insight Layer does not make decisions.

## Consequences

### Positive

- reusable insights
- better scalability
- cleaner separation of concerns

### Negative

- additional processing layer required

## Related ADRs

### Depends On

- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-103 — Provider Events Are Normalized Into Internal Events]]

### Enables

- [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]
- [[ADR-112 — Signals Use Time-Based Decay]]
- [[ADR-113 — Separate Operational and Historical Signals]]
- [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]
