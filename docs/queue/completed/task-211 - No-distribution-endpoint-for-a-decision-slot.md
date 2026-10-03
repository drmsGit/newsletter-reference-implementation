---
id: TASK-211
title: No distribution endpoint for a decision slot
status: Done
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-03 13:14'
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

Re-verified 2026-10-03: covered since 2026-10-02 (commit 8ebaae7, task-50 B22). GET /campaigns/decision-slots/{slot_id}/stats (backend/app/campaigns/router.py, get_decision_slot_stats) returns top_content from decision_slot_stats (backend/app/campaigns/service.py): resolutions of the slot grouped by content record and version, with selection_count and share in percent of the slot's resolutions. Tested by backend/tests/test_read_models.py::TestB21B22DecisionSlotStats::test_the_stats_carry_share_and_reasons. Known limits, deliberately left: capped at the top 20, and grouped by record AND version, so a record picked under two versions appears twice. Decided with the user 2026-10-03 to close as covered rather than add a full paged record-only distribution.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
No new code: the distribution Q3.7 asked for already exists as top_content on the slot stats route (2026-10-02). Verified against the route, the service and its test; limits (top 20, per version) recorded in the notes. The React decision-slot screen built 2026-10-03 shows it.
<!-- SECTION:FINAL_SUMMARY:END -->
