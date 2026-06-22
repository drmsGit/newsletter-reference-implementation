---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - rendering
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]"
enables:
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
---


## Status

Accepted

## Context

A Decision Slot may not always find suitable content.

Mandatory fallback content would reduce the automation benefit.

## Decision

If no suitable content is found, the Decision Slot may be hidden.

If no meaningful newsletter content remains, the email must not be sent.

Fallback content is optional.

## Consequences

### Positive

- avoids irrelevant fallback content
- reduces manual preparation effort
- prevents empty or meaningless emails

### Negative

- sendability checks are required

## Related ADRs

### Depends On

- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]

### Enables

- [[ADR-061 — Snapshot Based Final Rendering]]
