---
id: TASK-176
title: >-
  `ContentCategoryAssignmentDB.score` has no validation at write or read time —
  can be zero (degenerate/meaningless; "no relevance" should mean no assignment
  row, not a stored zero) or exceed the 0-10…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `ContentCategoryAssignmentDB.score` has no validation at write or read time — can be zero (degenerate/meaningless; "no relevance" should mean no assignment row, not a stored zero) or exceed the 0-10 range, and `RecipientPreferenceDB.new_score` has no ceiling so it can grow unbounded, compounding into `RecipientTopScoreStrategy`'s ranking (`recipients/service.py:135,170`). Fix now: reject a score of exactly zero at write time. The 0-10 range itself is a POC-only convention, not a hard rule — fold into the existing config-layer future work (Insight Q2) so a deployment can set its own limits rather than hardcoding 0-10. Source: [[Interview Prep - Decision, Overrides, Insight]] → Insight Q4. **Done 2026-07-12.** Verified live: score=0 rejected with a 400.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 581, section "Done", position 40 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
