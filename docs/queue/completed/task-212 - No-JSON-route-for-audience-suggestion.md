---
id: TASK-212
title: No JSON route for audience suggestion
status: Done
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-02 19:16'
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

Re-verified 2026-10-02. Both suggestion entry points the interview names (Q4.1, Manager Workflow interview lines 1217-1238) are now on the JSON plane: create a suggested group from a campaign, `POST /api/audience-groups/suggested` (`backend/app/audience/router.py:345-369`, task-50 C13), and re-suggest, `POST /api/audience-groups/{id}/recalculate` (`:262`). `suggest_include_blocks_for_campaign` and `campaign_category_scores` are reached through those two and have no route of their own. That is deliberate: Q4.1's resolution is 'the system suggests and the manager adjusts', which means a group is created and then edited, and nothing in the interview asks for a read-only preview without creating a group. If a screen later wants 'show me what would be suggested' first, that is a new item, not this one. One deviation, recorded: the interview filed the route 'under campaigns'; it lives under /api/audience-groups with campaign_id in the body. Functionally both entry points (campaign workspace, audience screen) call the same route. Cross-brand refusal is covered in `backend/tests/test_read_models.py:531-532`. The Jinja path (`backend/app/frontend/router.py:3255`) still calls the service directly; Jinja is frozen, so it is left as is.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed as done by task-50 (C13): suggestion and re-suggestion both have JSON routes, POST /api/audience-groups/suggested and /{id}/recalculate. Verified by reading the routes against the Q4.1 resolution and by the cross-brand test in test_read_models.py. No read-only preview route, deliberately (see notes).
<!-- SECTION:FINAL_SUMMARY:END -->
