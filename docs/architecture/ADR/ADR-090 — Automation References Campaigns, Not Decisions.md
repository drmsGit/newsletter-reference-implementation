---
type: adr
status: accepted
topic:
  - architecture
  - automation
  - campaign
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
  - "[[ADR-056 — Engagement Events as Foundation for Automation]]"
enables:
  - "[[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]"
---


## Status

Accepted

## Context

Automation flows need to orchestrate communication steps.

Content decisions should remain in the Decision Layer.

## Decision

The Automation Layer references campaigns.

It does not directly make content decisions.

A campaign may contain variants and Decision Slots that are resolved later.

## Consequences

### Positive

- clear separation of responsibilities
- simpler automation flows
- reusable campaigns
- decision logic remains centralized

### Negative

- campaign and decision models must be connected cleanly

## Related ADRs

### Depends On

- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-056 — Engagement Events as Foundation for Automation]]

### Enables

- [[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]
