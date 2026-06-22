---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - ai
  - governance
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-011 — Store Reusable Content Only]]"
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
---


## Status

Accepted

## Context

AI may suggest useful content, topics or campaign ideas.

However, production emails must only contain approved content.

## Decision

AI may recommend, rank, draft or suggest content.

AI may not publish unapproved content or bypass content governance.

Production decisions may only use approved Content Records.

## Consequences

### Positive

- safer production workflows
- clear governance boundary
- prevents unreviewed AI output from being sent

### Negative

- human review remains necessary for new content

## Related ADRs

### Depends On

- [[ADR-011 — Store Reusable Content Only]]
- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]
