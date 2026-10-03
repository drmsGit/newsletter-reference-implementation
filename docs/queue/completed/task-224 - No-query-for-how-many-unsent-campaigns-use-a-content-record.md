---
id: TASK-224
title: No query for how many unsent campaigns use a content record
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-03 18:39'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200370
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** No query for *"how many unsent campaigns use this record"*. From the resolution: **a catalogue edit being visible to other campaigns is the point of a catalogue, not a hazard.** The hazard is *silence* about reach — which is why 3.7 exists and why the count is passive.

| # | Gap | Where |
|---|---|---|
| 17 | No query for "how many unsent campaigns use this record" | new |

Source: [[Variant Editor - design interview]] → What Cluster 3 produced, gap 17 (Q3.1, 3.7).

**Verified against the code 2026-09-27:** the nearest thing is the delete guard at `backend/app/content/service.py:750-754`, which counts every `ModuleInstanceDB` row for a record with no campaign or sent/unsent filter.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. unsent_campaigns_using(db, content_record_id, *, brand_id) in campaigns/monitoring.py: campaigns in the brand with a module bound to the record, kept when any variant using it has a monitoring stage other than 'sent' (the monitoring screen's own definition, task-216).
2. GET /content/{id}/unsent-campaigns -> {count, campaigns: [{id, name}]}; 404 outside the brand; no owner names (ADR-178 point 8).
3. Tests incl. a sent variant excluded, a composing one counted, a campaign counted once, another brand's campaign excluded; mutation-checked.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-03. Built: unsent_campaigns_using in backend/app/campaigns/monitoring.py (campaigns with a module bound to the record, kept when a variant using it has a monitoring stage other than 'sent', so the composer's count and the monitoring screen share one definition); GET /content/{id}/unsent-campaigns -> {count, campaigns: [{id, name}]}, 404 outside the brand. Only bound modules count, not a slot that might pick the record. Tests backend/tests/test_content_reach.py (3); mutants: sent counted, any campaign counted, no brand check: each caught. A first full run failed with 89 errors because the parallel test-database session (worktree nostalgic-feynman) dropped tables mid-run; the rerun alone: 1182 passed, rc 0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GET /content/{id}/unsent-campaigns answers how many unsent campaigns use a record, and which (ids and names only), using the monitoring screen's definition of sent. Verified by 3 tests and three mutants; full suite 1182 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
