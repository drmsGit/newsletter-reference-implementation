---
id: TASK-209
title: >-
  GET /approvals/ accepts only status — no action-type or requester filter, no
  pagination
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-03 09:52'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-03. Governing: ADR-142 §4 (approval inbox, expiry read from the timestamp), ADR-166 point 3 (requester is a durable actor, so a filter dimension), ADR-172 (brand-scoped). Interview Q1.3: one flat list, newest first, filtered by action type and by requester.
1. `backend/app/approvals/service.py` list_for_brand gains keyword filters action_key, requested_by_type, requested_by_id, plus limit/offset. Status moves from a Python post-filter into SQL (paging over a post-filtered list would page the wrong rows). The SQL predicate sits beside is_expired/effective_status, and a test proves both agree on every case, deadline boundary included (the drift the is_expired docstring warns about). Order: created_at desc, then id desc, for stable pages.
2. `backend/app/approvals/router.py` GET /approvals/: the new query params; limit Query(50, 1..200) and offset, returning a plain list, as GET /delivery/send-instances does (DECISION, user: the envelope and total are task-88's).
3. The Jinja caller (`backend/app/frontend/router.py:3560`) keeps calling with no limit, so its behaviour is unchanged.
Not touched: the React inbox (no filter UI in this task), task-88.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Built 2026-10-03 as planned. `backend/app/approvals/service.py`: _status_clause (effective_status as SQL, next to is_expired) plus filters and paging in list_for_brand. `backend/app/approvals/router.py`: action_key, requested_by_type, requested_by_id, limit (50, max 200), offset. Tests: `backend/tests/test_approvals_list.py` (5), including the drift guard comparing SQL status with effective_status over six rows, one exactly at its deadline. 7 mutants caught, including the off-by-one at the deadline. The id tie-breaker isn't separately provable with distinct timestamps; it's defensive. All approval suites pass (74). Full suite rc=0. The Jinja inbox is unchanged (no limit). The React inbox has no filter UI yet; that wasn't in scope.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The approval inbox can be narrowed by action type and requester and paged with limit/offset in the database. The pending/decided rule moved into SQL beside is_expired, with a test holding the two to the same answers at the deadline boundary. Verified: 5 tests, 7 mutants caught, full suite passed.
<!-- SECTION:FINAL_SUMMARY:END -->
