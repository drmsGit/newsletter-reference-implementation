---
id: TASK-217
title: Audience membership records no reason
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-06 20:00'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200410
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Audience membership records **no reason**, and the case that needs one is external automation, not the in-app suggestion function — an orchestrator selecting recipients daily for a reactivation send must say *why this recipient*, and with AI in the loop the platform cannot reconstruct it. `POST /api/audience-groups/{id}/members/{id}` takes **no request body at all**.

Source: [[Manager Workflow - design interview]] → What Cluster 1 produced ("one gap that belongs to Cluster 4 but was found here").

**Verified against the code 2026-09-27:** `add_member(group_id, recipient_id)` takes no body (`backend/app/audience/router.py:77-78`); bulk add's `BulkAddRequest` (`backend/app/audience/models.py:59`) carries recipient ids only; the membership row (`backend/app/audience/db_models.py:41-51`) has `id`, `group_id`, `recipient_id` and `added_at`.

Related: task-107 (membership removal and expiry), which notes the row has no record of who added it or why.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-06: decided in the task-293 interview — a hand-add takes an optional reason and records who added it (Audience Write Surface final design pass, decision 5). Built by task-295; close this when that lands.
<!-- SECTION:NOTES:END -->
