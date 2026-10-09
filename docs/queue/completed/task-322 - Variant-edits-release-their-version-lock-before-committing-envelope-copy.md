---
id: TASK-322
title: Variant edits release their version lock before committing envelope copy
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 09:00'
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
- [x] #1 The version check, variant update and envelope update commit as one atomic edit.
- [x] #2 Overlapping envelope writers cannot both succeed with a lost update under the stated version-token contract.
- [x] #3 A failed envelope write does not leave a partially committed variant edit.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-8) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: update_variant commits at backend/app/campaigns/service.py:382, releasing the lock taken by refuse_stale, before set_envelope_fields (:446) writes and commits separately.

2026-10-09: fixed (commit 872caab; CI green).

Change: set_envelope_fields (backend/app/campaigns/service.py) takes a keyword-only commit switch, flushing instead of committing when False; its default is unchanged for its other callers (create_variant_for_campaign and the AI subject action). update_variant no longer commits the rename before the envelope: name, updated_at and envelope are written under the lock refuse_stale took and committed once (ADR-180 point 2).

Tests (backend/tests/test_envelope_lock.py):
- Two threads with their own sessions. A pauses inside its envelope write. B reads the current token and writes its own envelope. Then A resumes. If B was accepted, its envelope must be the one that stands; if B was refused as stale, A's stands. Before the fix, B was accepted and then silently overwritten by A: the review's lost update, reproduced.
- A failed envelope write leaves no half-committed rename (AC #3).
Mutation check: going back to two commits fails both. Full suite: 1554 passed.

No live check. It needs two editors racing on one variant; the threaded test drives the real service and database.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A variant's rename and envelope copy now commit together under the version lock, so a second editor is either refused as stale or goes strictly after, and is never silently overwritten. A failed envelope write leaves no half-committed edit. Verified by a threaded lost-update test that reproduced the defect, a partial-commit test, a mutation check, the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
