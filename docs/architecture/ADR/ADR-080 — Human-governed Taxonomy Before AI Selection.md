---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - ai
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
  - "[[ADR-079 — Dynamic Resolution Outside Builder]]"
enables:
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
---


## Status

Accepted

## Context

AI-based content selection can become unpredictable if it can freely choose from all available content.

The architecture needs business control over which content may be selected.

## Decision

Content selection must be based on a human-governed taxonomy.

Humans define:

- categories
- subcategories
- category relations
- content scoring
- relevance boundaries

AI may use this structure for ranking and recommendation.

## Consequences

### Positive

- business control remains intact
- less black-box behavior
- better content governance
- safer automation

### Negative

- taxonomy maintenance is required

## Related ADRs

### Depends On

- [[ADR-010 — Newsletter Content Source of Truth]]
- [[ADR-079 — Dynamic Resolution Outside Builder]]

### Enables

- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]
