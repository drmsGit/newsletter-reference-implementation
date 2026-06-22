---
type: adr
status: accepted
topic:
  - architecture
  - boundaries
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
enables:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-125 — Define a Minimal Reference Architecture]]"
---


## Status
Accepted

## Context
The newsletter architecture is intended to explain and implement the core concepts of modular newsletter systems.
It is not intended to become a full CRM, CDP, ERP, CMS, data warehouse, consent management platform or identity resolution system.
Those systems may be connected, but they are outside the core architecture.

## Decision
Keep the core architecture focused on newsletter-specific responsibilities:
- content source of truth
- newsletter composition
- module system
- rendering
- snapshots
- provider abstraction
- optional automation and decision layers

External enterprise systems remain integration points, not core components.

## Consequences

### Positive
- keeps the architecture focused
- reduces scope creep
- supports vendor neutrality
- makes the system easier to explain, implement and teach

### Negative
- integrations with external systems still require clear contracts
- some companies may expect CRM, consent or identity logic to be part of the same platform

## Notes
This boundary is especially important because the project is not meant to compete with enterprise suites. It explains architecture principles and provides a reference implementation.

## Related ADRs

### Enables

- [[ADR-002 — API First Architecture]]
- [[ADR-010 — Newsletter Content Source of Truth]]
- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-125 — Define a Minimal Reference Architecture]]
