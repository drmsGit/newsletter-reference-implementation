---
id: TASK-206
title: 'A content-readiness approvable action, plus its APPROVABLE_ROUTES entry'
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-04 18:25'
labels:
  - backend
dependencies:
  - TASK-282
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
<!-- SECTION:NOTES:END -->
