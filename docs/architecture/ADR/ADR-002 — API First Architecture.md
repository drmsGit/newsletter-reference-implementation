---
type: adr
status: accepted
topic:
  - architecture
  - api
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
enables:
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
---


## Status
Accepted

## Context
The architecture should allow components to be exchanged, extended or implemented in different technologies.
Direct coupling between UI, data storage, rendering and provider logic would make the system hard to replace or adapt.

## Decision
Use API-first communication between major components.
The Content Catalog, Builder, Rendering Layer, Provider Layer and optional Automation or Decision Layers should expose or consume defined interfaces instead of relying on direct internal coupling.

## Consequences

### Positive
- improves replaceability of components
- supports vendor neutrality
- enables external automation tools
- makes the architecture easier to test and document
- allows different implementation technologies

### Negative
- requires more explicit interface design
- adds overhead compared with direct database access
- versioning of APIs becomes important

## Notes
The principle does not require every small internal function to be an API. It applies to architectural boundaries between components.

## Related ADRs

### Enables

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
