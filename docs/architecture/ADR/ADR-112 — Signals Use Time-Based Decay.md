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
enables:
  - "[[ADR-113 — Separate Operational and Historical Signals]]"
---


## Status

Accepted

## Context

Older engagement data becomes less relevant for operational decisions.

## Decision

Signals should lose influence over time.

Implementations may choose different decay models.

Recent engagement should generally receive higher weighting.

## Consequences

### Positive

- more relevant personalization
- better audience quality
- reflects current user interests

### Negative

- decay logic must be maintained

## Related ADRs

### Depends On

- [[ADR-110 — Insight Layer Transforms Events Into Signals]]

### Enables

- [[ADR-113 — Separate Operational and Historical Signals]]
