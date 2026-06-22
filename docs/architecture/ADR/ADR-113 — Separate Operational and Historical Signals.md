---
type: adr
status: accepted
topic:
  - architecture
  - insight
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
  - "[[ADR-112 — Signals Use Time-Based Decay]]"
enables:
  - "[[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]"
---


## Status

Accepted

## Context

Operational decisions and long-term learning have different data requirements.

## Decision

The architecture distinguishes between:

- Operational Signals
- Historical Signals

Operational Signals prioritize recent behavior.

Historical Signals may include longer time periods for learning and analysis.

## Consequences

### Positive

- better decision quality
- better support for AI and recommendations
- cleaner separation of use cases

### Negative

- two signal perspectives must be maintained

## Related ADRs

### Depends On

- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
- [[ADR-112 — Signals Use Time-Based Decay]]

### Enables

- [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]
