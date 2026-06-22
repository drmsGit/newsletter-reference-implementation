---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - personalization
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
enables:
  - "[[ADR-086 — Decision Slots Fail Gracefully]]"
---


## Status

Accepted

## Context

Dynamic areas may require one content item or multiple content items.

Examples include one personalized hero or three recommended content blocks.

## Decision

A Decision Slot may resolve one or multiple Content Records.

The slot must define limits such as:

- minimum items
- maximum items
- allowed categories
- excluded categories
- allowed content types
- optional fallback content

## Consequences

### Positive

- supports flexible personalization
- works for single and multi-content modules
- keeps dynamic selection structured

### Negative

- slot configuration becomes more important

## Related ADRs

### Depends On

- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]

### Enables

- [[ADR-086 — Decision Slots Fail Gracefully]]
