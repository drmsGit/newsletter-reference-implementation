---
type: adr
status: accepted
topic:
  - architecture
  - content
  - data-model
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
enables:
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
---


## Status
Accepted

## Context
A content record should not merely represent a generic object such as a product, destination or topic.
For newsletter automation, it is more useful when a record represents a reusable communication unit with a clear editorial meaning.

## Decision
A Content Record represents a reusable communication unit.
It contains a specific message or content angle, plus the fields and metadata required to use that message in newsletter modules.

## Consequences

### Positive
- avoids overly generic records
- improves editorial clarity
- supports better content selection
- makes automation and AI recommendations more precise
- separates knowledge updates from new communication topics

### Negative
- may create more records than a pure object-based model
- requires clear editorial rules for when to update a record and when to create a new one

## Notes
Updating a record should correct or improve the same communication unit. A different topic, angle or seasonal message should usually become a new record.

## Related ADRs

### Depends On

- [[ADR-010 — Newsletter Content Source of Truth]]

### Enables

- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]
