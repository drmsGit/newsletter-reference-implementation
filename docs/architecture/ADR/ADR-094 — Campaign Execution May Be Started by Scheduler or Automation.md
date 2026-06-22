---
type: adr
status: accepted
topic:
  - architecture
  - automation
  - delivery
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-022 — Delivery Type Is Independent From Composition]]"
  - "[[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]"
enables:
  - "[[ADR-095 — Use Send Instances for Technical Execution Tracking]]"
---


## Status

Accepted

## Context

Campaigns may be sent in different ways.

Some are scheduled manually.

Others are started by automation flows or external triggers.

## Decision

Campaign execution may be started by:

- scheduler
- automation layer
- external trigger
- manual action

The execution mechanism should not change the campaign composition model.

## Consequences

### Positive

- supports single sends and automations
- keeps campaign model stable
- flexible integration

### Negative

- execution context must be tracked

## Related ADRs

### Depends On

- [[ADR-022 — Delivery Type Is Independent From Composition]]
- [[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]

### Enables

- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
