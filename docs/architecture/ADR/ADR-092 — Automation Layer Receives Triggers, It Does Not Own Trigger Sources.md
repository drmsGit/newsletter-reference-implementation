---
type: adr
status: accepted
topic:
  - architecture
  - automation
  - integration
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]"
enables:
  - "[[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]"
---


## Status

Accepted

## Context

Triggers may originate from different systems depending on the business model and system landscape.

Examples include CRM, DWH, shop systems, event stores, schedulers or external automation tools.

## Decision

The Automation Layer must process triggers.

It does not need to own the systems where triggers originate.

A trigger should provide enough context for the automation to continue.

## Consequences

### Positive

- system-agnostic integration
- flexible adoption
- clear boundary between source systems and automation

### Negative

- trigger payloads must be standardized

## Related ADRs

### Depends On

- [[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]

### Enables

- [[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]
