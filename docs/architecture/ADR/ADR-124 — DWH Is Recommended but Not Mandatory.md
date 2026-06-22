---
type: adr
status: accepted
topic:
  - architecture
  - dwh
  - data
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-125 — Define a Minimal Reference Architecture]]"
enables:
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
  - "[[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]"
---


## Status

Accepted

## Context

Some organizations operate without a dedicated data warehouse.

Others rely heavily on centralized analytical platforms.

## Decision

A DWH or comparable analytical data store is recommended but not mandatory.

The minimal architecture can operate without a DWH.

Advanced capabilities such as:

- audience intelligence
- recommendation systems
- automation
- AI-assisted decisions
- cross-channel analytics

benefit significantly from a centralized analytical data store.

## Consequences

### Positive

- low adoption barrier
- supports small organizations
- scalable growth path

### Negative

- advanced capabilities may be limited without a DWH

## Related ADRs

### Depends On

- [[ADR-125 — Define a Minimal Reference Architecture]]

### Enables

- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
- [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]
