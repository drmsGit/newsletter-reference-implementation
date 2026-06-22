---
type: adr
status: accepted
topic:
  - architecture
  - overrides
  - rendering
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-040 — Introduce Override Layer]]"
enables:
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
---


## Status
Accepted

## Context
When a newsletter uses a content reference and also contains overrides, the system must define which value is authoritative.
Without a clear precedence rule, preview, rendering and editing can behave inconsistently.

## Decision
Overrides take precedence over referenced catalog content.
If an override exists for a field, the override value is used until it is deleted or reset.
If no override exists, the referenced catalog value is used.

## Consequences

### Positive
- creates deterministic rendering
- makes campaign-specific changes explicit
- protects editors from unexpected catalog updates where they intentionally overrode content
- supports clear reset-to-original behavior

### Negative
- overridden fields no longer receive catalog updates
- users must understand when content is original or modified
- usage views must show override state

## Notes
The effective content resolution order is: override value, referenced content value, fallback if defined.

## Related ADRs

### Depends On

- [[ADR-040 — Introduce Override Layer]]

### Enables

- [[ADR-061 — Snapshot Based Final Rendering]]
