---
id: TASK-213
title: >-
  resolve_audience returns only the final list, discarding the arithmetic it
  computed
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 207800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **`resolve_audience` returns only the final list** (Q3), discarding the arithmetic it computed: included by rules, added by hand, removed by exclusions, dropped by consent. The numbers exist inside the function.

Source: [[Manager Workflow - design interview]] → What Cluster 4 produced, gap 13 (Q4.3).

**Verified against the code 2026-09-27:** `resolve_audience` (`backend/app/audience/service.py:514-516`) returns `list[RecipientDB]`; the include / exclude / pin / consent sets are local variables at `:563-590`.

Related: task-47 changes the precedence inside the same function ([[ADR-176 — A Negative Decision Outranks a Positive One]] point 1).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
