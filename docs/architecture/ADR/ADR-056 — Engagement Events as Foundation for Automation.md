---
type: adr
status: accepted
topic:
  - architecture
  - automation
  - analytics
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-055 — Separate Delivery Execution from Engagement Events]]"
enables:
  - "[[ADR-090 — Automation References Campaigns, Not Decisions]]"
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
---


## Status

Accepted

## Context

Automation, recommendations and AI features require behavioral data.

Provider-specific event structures create lock-in.

## Decision

Automation and recommendation systems should operate on a provider-independent engagement event model.

Examples:

- opens
- clicks
- conversions
- unsubscribes
- bounces

## Consequences

### Positive

- provider independence
- consistent analytics
- reusable automation logic

### Negative

- event normalization required

## Related ADRs

### Depends On

- [[ADR-055 — Separate Delivery Execution from Engagement Events]]

### Enables

- [[ADR-090 — Automation References Campaigns, Not Decisions]]
- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
