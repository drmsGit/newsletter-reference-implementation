---
id: TASK-173
title: >-
  `DecisionResolutionDB.score` is stored as `Integer`, so
  `score=int(result.score)` (`decision/service.py:42`) silently truncates the
  weighted float score `recipient_top_score` computes — two candidate…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `DecisionResolutionDB.score` is stored as `Integer`, so `score=int(result.score)` (`decision/service.py:42`) silently truncates the weighted float score `recipient_top_score` computes — two candidates differing only in fractional score (12.4 vs 12.9) both round to 12, losing tie-breaking/explainability granularity relevant to ADR-085. Fix: change the column to a proper decimal/float type (e.g. `Numeric`) and drop the `int()` cast. Source: [[Interview Prep - Decision, Overrides, Insight]] → Decision Q6. **Done 2026-07-12** — column changed to `Float`, `int()` cast dropped. Verified live: a fractional score (860.0) now persists exactly instead of rounding.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 575, section "Done", position 37 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
