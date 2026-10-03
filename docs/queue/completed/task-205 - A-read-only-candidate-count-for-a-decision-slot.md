---
id: TASK-205
title: A read-only candidate count for a decision slot
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-03 13:17'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200390
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **A read-only candidate count for a decision slot** (Q4b). `POST /decision/slots/{id}/execute` resolves for real and writes a `DecisionResolution`, so there is no way to ask what a slot would choose between without causing a decision.

Source: [[Manager Workflow - design interview]] → What Cluster 2 produced, requirement 2 (Q2.4b).

**Verified against the code 2026-09-27:** `backend/app/decision/router.py:25-40` is the only slot route. `execute_decision_slot` (`backend/app/decision/service.py:12`) updates a resolution in place (`:90-96`) or creates one (`:104-113`). There is no count or dry-run route.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Lift the candidate query both strategies copied into decision/strategies/base.py:candidate_query(db, slot, *, brand_id); strategies keep their own ordering/signal filtering.
2. campaigns/service.py:slot_candidate_count(db, slot_id, *, brand_id) counts distinct records over it, writes nothing.
3. GET /campaigns/decision-slots/{slot_id}/candidates -> SlotCandidates (slot_id, candidate_count, category_ids, requires_recipient); 404 foreign, 409 broken chain, 400 unknown strategy.
4. Tests in test_read_models.py::TestSlotCandidateCount on a fresh brand, mutation-checked.
5. React decision-slot screen consumes it (same session).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-03: built. Backend commit 153da7b: candidate_query lifted into backend/app/decision/strategies/base.py (both strategies call it); campaigns/service.py:slot_candidate_count; GET /campaigns/decision-slots/{slot_id}/candidates -> SlotCandidates. Tests backend/tests/test_read_models.py::TestSlotCandidateCount (6), on a fresh brand; seven mutants (no distinct, no status filter, no brand filter, no category filter, requires_recipient hard-coded, service resolving, no brand scoping) each caught. Full suite 1101 passed, rc 0. Client commit 19861ec: DecisionSlots + DecisionSlotDetail screens consume it; 71 client tests; check:contract clean after commit. Browser: /manager/decision-slots/1 showed 85 candidates, only GETs, pick count unchanged at 40.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A slot's candidates can be counted without resolving it: GET /campaigns/decision-slots/{id}/candidates counts distinct records over the same query the strategies now share, and writes nothing. Shown on the new read-only decision-slot screen. Verified by 6 mutation-checked backend tests, client tests, and a browser check that opening a slot makes only GET requests.
<!-- SECTION:FINAL_SUMMARY:END -->
