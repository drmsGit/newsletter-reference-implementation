---
type: adr
status: accepted
topic:
  - architecture
  - audience
  - crm
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]"
enables:
  - "[[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]"
  - "[[ADR-104 — Audience Ownership Stays Outside Provider]]"
---


## Status

Accepted

## Context

Audience definitions may originate from business users or be suggested by automation and AI systems.

Different audiences have different lifecycles.

## Decision

Long-term reusable audiences belong in the CRM.

Temporary or campaign-specific audiences may exist in the Audience Layer.

AI-generated audience suggestions are not automatically authoritative.

## Consequences

### Positive

- clear audience ownership
- supports experimentation
- prevents uncontrolled audience growth

### Negative

- audience synchronization may be required

## Related ADRs

### Depends On

- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]

### Enables

- [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]
- [[ADR-104 — Audience Ownership Stays Outside Provider]]
