---
id: TASK-202
title: An override on a slot-bound module is permitted and should be refused
status: Done
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-02 14:39'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** An override on a slot-bound module is permitted and should be refused. From the cluster's reversal: `ContentOverrideDB`'s docstring names *"a consistent headline across the personalized picks"* as the intended use of the override layer. Question 2.6 forbids exactly that: **a decision slot may not be overridden.** An override on a slot defeats the slot, and once `max_results` works it produces three personalised picks wearing one pinned headline. So an override attaches to a **catalogue-bound** module only — enforceable, not conventional.

The interview logged this twice, as one piece of work:

| # | Gap | Where |
|---|---|---|
| 15 | An override on a slot-bound module is permitted and should be refused | `overrides/`, `rendering/service.py:286` |
| 20 | Nothing refuses an override on a slot-bound module (also gap 15) | `overrides/service.py` |

Source: [[Variant Editor - design interview]] → What Cluster 2 produced, gap 15 (Q2.6), and What Cluster 3 produced, gap 20.

**Verified against the code 2026-09-27:** `backend/app/overrides/service.py:32` refuses only when both `content_record_id` and `decision_slot_id` are None, so a slot-bound module passes into `create_content_override` (`:68`). The override is then applied at `backend/app/rendering/service.py:286` and `:301`. The docstring the interview reversed still states the old intent.

Related: [[ADR-178 — Scope of the Correction, Not Location of the Manager]]; task-109 (`max_results`).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Creating an override on a slot-bound module is refused
- [x] #2 An override row on a module later bound to a slot does not apply
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-02: still true. Refused in overrides.service._overrideable_manifest; get_active_content_override joins the module and ignores slot-bound ones (covers rebinding, which update_module allows). The existing override tests were built on the forbidden case (field_override fixture on a slot module, reason 'Consistent headline across the personalized picks'); moved to the catalogue-bound static_module, and 'creates on decision module' became the refusal test. Two failing tests first, both mutants caught. Seed creates no overrides. Suite 904 passed. ADR-178 also owes a dated addendum on ADR-040 (its own Consequences say so) — not done here.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An override can no longer attach to a module bound to a decision slot: creation is refused and the render lookup ignores any such row, so rebinding cannot reintroduce one. Verified by two new tests that failed first and catch their mutants; full suite 904 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
