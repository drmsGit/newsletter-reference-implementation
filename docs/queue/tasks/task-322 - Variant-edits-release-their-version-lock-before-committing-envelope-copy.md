---
id: TASK-322
title: Variant edits release their version lock before committing envelope copy
status: To Do
assignee: []
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 08:23'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: medium. Two valid optimistic-concurrency writes can succeed while one silently overwrites the other's envelope. Reachable today under concurrent edits.

Evidence: backend/app/campaigns/service.py:342-357 refreshes the variant FOR UPDATE and checks expected_updated_at. update_variant commits the name/version at line 380, releasing that lock, before calling set_envelope_fields at 382. The helper writes the separate module and commits at line 509.

Reproducer test to implement: caller A updates using token t0 and pauses immediately after its first commit, before set_envelope_fields. Caller B reads token t1, updates its envelope using t1 and completes. Resume A: its envelope overwrites B's accepted envelope without a stale-write refusal, even though A never observed B's version. Use independent database sessions and a barrier; no new reproducer was executed in this continuation.

ADR-180 point 2 promises the version-check backstop against silent lost edits. Hold the lock and version change through the entire variant-plus-envelope write in one transaction; the public helper's transaction ownership must allow that.

Related: completed task-110 added variant concurrency; task-309 concerns where the helpers live, not their transaction lifetime; task-124 concerns broader contention.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The version check, variant update and envelope update commit as one atomic edit.
- [ ] #2 Overlapping envelope writers cannot both succeed with a lost update under the stated version-token contract.
- [ ] #3 A failed envelope write does not leave a partially committed variant edit.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-8) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: update_variant commits at backend/app/campaigns/service.py:382, releasing the lock taken by refuse_stale, before set_envelope_fields (:446) writes and commits separately.
<!-- SECTION:NOTES:END -->
