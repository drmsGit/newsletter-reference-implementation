---
id: TASK-212
title: No JSON route for audience suggestion
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p1
type: feature
ordinal: 200350
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **No JSON route for audience suggestion** (Q1). `suggest_include_blocks_for_campaign`, `campaign_category_scores`, `create_suggested_group_for_campaign` and `recalculate_suggested_blocks` all exist and are reachable only from Jinja — and Q1 makes suggestion the *primary* way an audience comes into being.

Source: [[Manager Workflow - design interview]] → What Cluster 4 produced, gap 12 (Q4.1).

**Verified against the code 2026-09-27 — partial:** recalculation already has a JSON route, `POST /api/audience-groups/{id}/recalculate` (`backend/app/audience/router.py:183-191`, commit 07bf79e). Still Jinja-only: `create_suggested_group_for_campaign` (`backend/app/audience/service.py:706`, called only from `backend/app/frontend/router.py:3950`). No route at all: `suggest_include_blocks_for_campaign` (`:690`) and `campaign_category_scores` (`:619`).

Related: task-50 (logic living only in `frontend/router.py`).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
