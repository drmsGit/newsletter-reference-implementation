---
id: TASK-179
title: >-
  `record_outcome_delta` (`overrides/service.py:32-39`) replaces `outcome_delta`
  wholesale on each PATCH instead of merging keys — outcome data that arrives
  incrementally (e.g. open-rate today, click-r…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `record_outcome_delta` (`overrides/service.py:32-39`) replaces `outcome_delta` wholesale on each PATCH instead of merging keys — outcome data that arrives incrementally (e.g. open-rate today, click-rate a week later) has the second update silently overwrite the first entirely. `test_overrides.py:130-138` only checks non-`outcome_delta` fields survive; the merge case is untested and would currently fail. Fix: merge incoming keys into the existing `outcome_delta` dict instead of replacing it. Source: [[Interview Prep - Decision, Overrides, Insight]] → Overrides Q3. **Done 2026-07-12.** Verified live: two separate PATCH calls with different keys both landed in the final `outcome_delta`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 587, section "Done", position 43 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
