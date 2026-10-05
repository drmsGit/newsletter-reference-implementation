---
id: TASK-206
title: 'A content-readiness approvable action, plus its APPROVABLE_ROUTES entry'
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-05 18:10'
labels:
  - backend
dependencies:
  - TASK-283
  - TASK-210
priority: p2
type: feature
ordinal: 200430
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **A content-readiness approvable action**, plus its `APPROVABLE_ROUTES` entry (Q6b). That table is fail-closed by omission, so without the entry a machine asserting readiness gets a hard 403 rather than a hold.

Source: [[Manager Workflow - design interview]] → What Cluster 2 produced, requirement 3 (Q2.6b).

**Verified against the code 2026-09-27:** `APPROVABLE_ROUTES` (`backend/app/auth/policy.py:262-264`) holds a single entry, `send.fire_send_instance`. `backend/app/approvals/actions/` holds only `send_fire.py` and `ai_subject_apply.py`.

Related: [[ADR-174 — Channel Readiness Is Asserted, Not Computed]].
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-04: depends on task-282, the readiness state itself (split out of the task-274 design session).

2026-10-05 (task-282 design session):
- This now depends on task-283, the readiness state and routes, and on task-210: the readiness hold must carry no deadline (Manager Workflow Cluster 1, around line 358; ADR-142 addendum 2026-09-24).
- Until this task is built, task-283 refuses an integration's attempt to mark a record ready (nothing goes through unheld). An integration may still unmark directly; that is decided.
- Gap found 2026-10-05: an APPROVABLE_ROUTES entry alone will not hold a content.manage route. The guard raises ApprovalRequired only for SENDS_EXECUTE when the integration may not send unattended (backend/app/auth/dependencies.py, around 623-638), so it needs widening to the readiness route.
- The held payload carries path params only, so the channel must be a path parameter of the mark route.
<!-- SECTION:NOTES:END -->
