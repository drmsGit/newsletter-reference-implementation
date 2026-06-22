---
type: adr
status: accepted
topic:
  - architecture
  - automation
  - audience
  - ai
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
  - "[[ADR-123 — Audience Ownership Depends on Reuse]]"
enables:
  - "[[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]"
---


## Status

Accepted

## Context

CRM systems remain responsible for customer master data and manually created segments.

However, engagement and content data can reveal useful audience patterns.

## Decision

The architecture may include Audience Intelligence as a derived layer.

It may suggest audiences based on:

- engagement behavior
- clicked content
- content categories
- similarity patterns

Authoritative customer data remains in the CRM.

## Consequences

### Positive

- supports smarter targeting
- keeps CRM as customer source of truth
- enables AI-assisted audience discovery

### Negative

- suggested audiences require validation

## Related ADRs

### Depends On

- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
- [[ADR-123 — Audience Ownership Depends on Reuse]]

### Enables

- [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]
