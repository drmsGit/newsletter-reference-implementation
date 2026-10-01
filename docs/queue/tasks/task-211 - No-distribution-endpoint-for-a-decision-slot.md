---
id: TASK-211
title: No distribution endpoint for a decision slot
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200395
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **No distribution endpoint for a decision slot** (Q7). The answer is an aggregate over `DecisionResolutionDB` grouped by content record; nothing exposes one.

Source: [[Manager Workflow - design interview]] → What Cluster 3 produced, gap 9 (Q3.7).

**Verified against the code 2026-09-27:** no aggregate over `DecisionResolutionDB` anywhere in `backend/app/`. The only resolution routes are `backend/app/campaigns/router.py:286` (list) and `:299` (create).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
