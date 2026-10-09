---
id: TASK-320
title: >-
  A no-pick decision leaves an older ineligible resolution available to
  rendering
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 08:55'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. Rendering can use content that the current decision explicitly cannot select. Reachable today.

Evidence: backend/app/decision/service.py:60-63 returns None on an empty candidate result without representing that outcome in the resolution state. backend/app/rendering/frame.py:148-185 then selects the latest historical per-recipient or generic resolution and resolves its pinned version, without reapplying current candidate eligibility.

Reproduction: obtain a successful pick, remove that record's channel-readiness entry, execute the slot again and observe None, then render the slot. The previous now-unready record still appears. Reproduced during the first review stage. The same stale-result mechanism defeats changed category/status eligibility and can defeat the no-meaningful-content floor.

ADR-174 and ADR-179 require machine-eligible candidates; ADR-086 permits empty slots. Represent the current no-pick result and make a fresh render/send honor it while preserving legitimate historical as-sent evidence.

Related: completed task-284 repaired candidate eligibility and task-228 introduced the send floor. This downstream fallback bypasses those controls; task-234's decision-execution efficiency is related but different.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 After a previously successful pick becomes ineligible and a new execution returns no pick, a fresh render/send does not use the previous pick.
- [x] #2 Current no-pick outcomes remain distinct from immutable historical delivery evidence.
- [x] #3 The meaningful-content floor observes the actual current decision outcome.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-4) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: execute_decision_slot returns None on no result without recording it (backend/app/decision/service.py:62-63), and _pick_for_slot (backend/app/rendering/frame.py:148) takes the newest stored resolution.

2026-10-09: fixed (commit 7074102; CI green).

Design: no schema change. Recording a "no pick" resolution would need content_record_id to become nullable (it is NOT NULL, backend/app/campaigns/db_models.py), and every reader of resolutions to handle an empty one: rendering, monitoring, the slot statistics, delivery records. Instead, the send uses what it already knows. It runs each slot's decision immediately before rendering, so it collects the slots that found nothing in this run and tells the renderer.

Change:
- backend/app/delivery/service.py (_deliver_claimed): empty_slots collects every slot whose execute_decision_slot returned None or raised the "nothing found" ValueError. ConsentDenied is still re-raised.
- backend/app/rendering/frame.py: render_frame(..., empty_slots=frozenset()) renders those slots empty, with no fallback to the recipient's older pick and none to the slot's generic one.
- Stored resolutions, the history, are not touched (AC #2). The picks render_frame returns exclude the empty slots, so what_rendered and the meaningful-content floor see the actual outcome (AC #3).

Deliberately unchanged: a live preview, which runs no decision, still shows the last stored pick, as before. Making previews reflect a current no-pick would need the persisted null pick above. Noted as an option, not done.

Tests: backend/tests/test_stale_pick.py, reusing test_render_skip's world fixture. A person gets a pick on the first send; then the decision returns None (or raises the "nothing found" ValueError), and the second send must mail nobody and exclude the person with "render: nothing to show". Both tests failed before the fix: the stale pick was mailed. The world fixture's fake decision engine now returns its resolution, as the real one does; it returned None, which would have read as "found nothing" (backend/tests/test_render_skip.py). Mutation check: 3 of 3 caught (render ignoring empty_slots, a None result not remembered, a ValueError not remembered). Full suite: 1550 passed.

No live check. It would mean changing a real content record's readiness and sending a real campaign twice in the dev data. The tests drive the real send and render path.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A decision that finds nothing in this run is now honoured by the send: those slots render empty instead of reusing an older, no-longer-eligible stored pick. The meaningful-content floor sees the real outcome, and stored resolutions stay as history. Verified by two tests that mailed the stale pick before the fix, 3/3 mutants caught, the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
