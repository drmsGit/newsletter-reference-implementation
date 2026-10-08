---
id: TASK-109
title: >-
  `max_results` is dead configuration and a decision resolution cannot hold more
  than one pick.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 22:25'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 368, section "Features", position 62 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand): still true. The cited duplication line has drifted: max_results is copied at backend/app/campaigns/duplication.py:541, and the DecisionSlotDetail screen still displays it (frontend/src/screens/DecisionSlotDetail.tsx:68). Moved ahead of the parked block today, with task-220 (which depends on it) right after.
<!-- SECTION:NOTES:END -->
