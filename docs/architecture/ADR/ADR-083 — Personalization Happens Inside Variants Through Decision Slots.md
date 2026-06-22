---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - personalization
  - composition
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-021 — Variants Are Human Created Versions]]"
  - "[[ADR-079 — Dynamic Resolution Outside Builder]]"
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
enables:
  - "[[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]"
  - "[[ADR-090 — Automation References Campaigns, Not Decisions]]"
---


## Status

Accepted

## Context

Variants are intentionally created by humans.

If personalization created new variants automatically, the number of variants would become unmanageable.

## Decision

Personalization happens inside variants through Decision Slots.

A variant remains a human-created newsletter version.

Dynamic or personalized content is resolved within defined slots.

## Consequences

### Positive

- prevents variant explosion
- preserves editorial control
- allows personalization inside stable compositions
- supports recipient-level history

### Negative

- Decision Slot resolution must be tracked separately

## Related ADRs

### Depends On

- [[ADR-021 — Variants Are Human Created Versions]]
- [[ADR-079 — Dynamic Resolution Outside Builder]]
- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]

### Enables

- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
- [[ADR-090 — Automation References Campaigns, Not Decisions]]
