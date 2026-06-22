---
type: adr
status: accepted
topic:
  - architecture
  - automation
  - delivery
  - analytics
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-020 — Campaign Equals Newsletter]]"
  - "[[ADR-053 — Maintain Minimal Delivery Execution History]]"
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
  - "[[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]"
---


## Status

Accepted

## Context

A campaign is a business-level newsletter or email unit.

A concrete send may be triggered by a scheduler, automation or external event.

The architecture needs a technical object to track such executions.

## Decision

Use Send Instances for technical execution tracking.

A Send Instance is created when a concrete send is triggered.

It links:

- campaign
- variant
- snapshot
- delivery execution
- provider response
- engagement events

## Consequences

### Positive

- clean execution tracking
- supports recurring and triggered sends
- avoids confusing campaign runs with business campaigns

### Negative

- introduces another technical object

## Related ADRs

### Depends On

- [[ADR-020 — Campaign Equals Newsletter]]
- [[ADR-053 — Maintain Minimal Delivery Execution History]]
- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]
