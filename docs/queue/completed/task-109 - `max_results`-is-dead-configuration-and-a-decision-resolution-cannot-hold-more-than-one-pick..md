---
id: TASK-109
title: >-
  `max_results` is dead configuration and a decision resolution cannot hold more
  than one pick.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-11 19:46'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — one schema change unblocks the personalisation shape the user calls most likely, and the collision fix. Both found 2026-09-25, both verified.** **`max_results` is dead configuration and a decision resolution cannot hold more than one pick.** `DecisionSlotDB.max_results` (`backend/app/campaigns/db_models.py:115`) exists, defaults to 1, is carried by `DecisionSlotCreate`, exposed by the router and copied by `backend/app/campaigns/duplication.py:244` — and is **read by neither the decision engine nor the render path**. Every reference is CRUD. So a manager can configure *"show up to 3 content records"* today and it does nothing. The reason it does nothing is the second half: `DecisionResolutionDB.content_record_id` is a single non-null FK, one row per recipient per slot, and `resolve_content_for_module` (`backend/app/rendering/service.py:450`) takes `.first()`. **These are one piece of work.** Supporting `max_results` and supporting the ranked "queue of next content" the user proposed for multi-slot collisions need the same shape — several ranked picks per recipient per slot — so building either separately builds it twice. **Why it matters more than it looks:** [[Variant Editor - design interview]] question 1.6 established from business experience that several personalised spots interleaved with manual content is *rare*, and that **one slot yielding several records is the common case**. The capability that is already modelled, already configurable and already duplicated is the one that was never built. Sequence with the editor screens.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A slot shows up to its number of picks (1-5), best first, by repeating its module; fewer found, fewer shown
- [x] #2 Show up to is editable; a push slot is always 1
- [x] #3 No article appears twice in one email between slots: a later slot takes its next ranked picks
- [x] #4 Preview, send and the as-sent reconstruction all show every pick, each crediting its own record
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 368, section "Features", position 62 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand): still true. The cited duplication line has drifted: max_results is copied at backend/app/campaigns/duplication.py:541, and the DecisionSlotDetail screen still displays it (frontend/src/screens/DecisionSlotDetail.tsx:68). Moved ahead of the parked block today, with task-220 (which depends on it) right after.

2026-10-11, designed with the user one question at a time, recorded in the ADR-084 addendum of 2026-10-11. User decisions: several picks repeat the slot's module (no list modules); Show up to is 1-5, editable, push always 1, no minimum; slot-versus-slot duplicates handled now, hand-bound versus slot stays task-220 (next, on the same mechanism). Technical shape from the final-design pass: resolution rows gain rank and pick_set (migrate_0049, older rows are sets of one), read only through backend/app/decision/sets.py; strategies gain rank(limit, exclude) and execute is its first; execute_decision_slot stores a ranked set (global sets updated in place, a per-recipient set on a global slot only while an exclusion changes it, deleted once it no longer does); the send resolves slots in frame module order passing over what earlier slots show; frame, live render and reconstruction render one copy per pick; the as-sent view lists one row per copy. Decision slots CHECK max_results 1-5.
Verified: tests/test_several_picks.py (17), 19 mutations all killed (one survivor fixed by a stronger legacy-row test); DeliveryAsSent.test.tsx and SlotSettings.test.tsx (3 new), the row-key mutation killed; full pytest 1907 passed, Ruff clean, vitest 275, tsc clean. Live check on scratch campaign 16 (SCRATCH task-109 picks, duplicated from Demo Campaign 2): set Show up to 3 in the slot settings UI, resolved slot 8 for recipient 1, and the preview rendered the module three times (records 33, 35, 75, two tied at random as the reason discloses). Commit a407b12.
Not done here: a preview without a recipient can still show one record in two global slots (previews make no new picks), as the addendum says.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A decision slot now shows up to 1-5 picks, best first, its module repeated once per pick, and a later slot never repeats an article an earlier slot shows (ADR-084 addendum 2026-10-11). Show up to is editable in slot settings; push stays at one. Verified by 17 backend and 3 frontend tests with all mutations killed, full suites green, and a live check on a scratch campaign.
<!-- SECTION:FINAL_SUMMARY:END -->
