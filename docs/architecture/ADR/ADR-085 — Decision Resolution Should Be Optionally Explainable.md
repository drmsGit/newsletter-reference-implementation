---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - analytics
  - ai
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
  - "[[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]"
---


## Status

Accepted

## Context

Dynamic content decisions may need to be audited, explained or analyzed later.

However, storing full decision details may increase storage requirements.

## Decision

The architecture should allow Decision Slot resolutions to store explanation data.

The amount of stored explanation may vary by implementation.

Examples:

- decision strategy
- score
- matched categories
- expanded categories
- input signals
- approval status
- short reason summary

## Consequences

### Positive

- better transparency
- supports debugging
- useful for analytics and AI improvement

### Negative

- additional storage requirements
- explanation depth must be managed

## Current limitation
- Preference learning deltas are hardcoded
- Decision strategy weights are hardcoded
- strategy_config exists but is not yet evaluated by strategies.

## Related ADRs

### Depends On

- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]
- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
