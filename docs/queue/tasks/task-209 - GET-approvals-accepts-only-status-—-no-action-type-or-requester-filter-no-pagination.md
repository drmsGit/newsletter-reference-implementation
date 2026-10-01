---
id: TASK-209
title: >-
  GET /approvals/ accepts only status — no action-type or requester filter, no
  pagination
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p1
type: feature
ordinal: 200330
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **`GET /approvals/` accepts only `status`** (Q3) — no action-type filter, no requester filter, no pagination. The same requirement as Cluster 2's question 10 arriving on another route.

Source: [[Manager Workflow - design interview]] → What Cluster 1 produced, gap 7 (Q1.3).

**Verified against the code 2026-09-27:** `backend/app/approvals/router.py:56-72` — `list_pending(status=...)` is the only parameter; the service (`backend/app/approvals/service.py:412`) ends in `.all()` at `:425`.

Related: task-88 (one standard pagination mechanism) covers the paging half.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
