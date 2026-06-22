---
type: adr
status: accepted
topic:
  - architecture
  - foundation
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-001 — Newsletter Architecture Boundaries]]"
enables:
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
  - "[[ADR-060 — Rendering as Independent Layer]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
---


## Status

Accepted

## Context

Many organizations require a practical starting point before implementing advanced automation and AI capabilities.

## Decision

The reference architecture defines a minimal implementation path.

Minimal architecture:

CRM
→ Content Catalog
→ Newsletter Builder
→ Rendering Layer
→ Provider

Additional components such as:

- Automation Layer
- Decision Layer
- Insight Layer
- DWH
- Audience Intelligence

are optional extensions.

## Consequences

### Positive

- low entry barrier
- incremental adoption
- suitable for small teams

### Negative

- limited automation and personalization capabilities

## Related ADRs

### Depends On

- [[ADR-001 — Newsletter Architecture Boundaries]]

### Enables

- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-010 — Newsletter Content Source of Truth]]
- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]
- [[ADR-060 — Rendering as Independent Layer]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
