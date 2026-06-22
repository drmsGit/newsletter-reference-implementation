---
type: adr
status: accepted
topic:
  - architecture
  - automation
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-090 — Automation References Campaigns, Not Decisions]]"
  - "[[ADR-002 — API First Architecture]]"
enables:
  - "[[ADR-092 — Automation Layer Receives Triggers, It Does Not Own Trigger Sources]]"
  - "[[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]"
---


## Status

Accepted

## Context

General workflow tools such as n8n can handle complex automation.

The reference architecture should not rebuild a full workflow engine.

## Decision

The Automation Layer provides newsletter-specific orchestration.

It may support:

- triggers
- waits
- rules
- campaign references
- API calls
- webhooks

It should not replace general-purpose workflow tools.

## Consequences

### Positive

- avoids unnecessary complexity
- works with existing automation platforms
- focuses development on newsletter-specific value

### Negative

- external tooling may be required for complex workflows

## Related ADRs

### Depends On

- [[ADR-090 — Automation References Campaigns, Not Decisions]]
- [[ADR-002 — API First Architecture]]

### Enables

- [[ADR-092 — Automation Layer Receives Triggers, It Does Not Own Trigger Sources]]
- [[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]
