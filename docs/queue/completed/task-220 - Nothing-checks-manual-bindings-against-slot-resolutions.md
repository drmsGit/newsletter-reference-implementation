---
id: TASK-220
title: Nothing checks manual bindings against slot resolutions
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-11 20:06'
labels:
  - backend
dependencies:
  - TASK-109
priority: p3
type: feature
ordinal: 202060
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Nothing checks manual bindings against slot resolutions. The principle it enforces: **Human beats system, and it is a different axis from [[ADR-176 — A Negative Decision Outranks a Positive One]] (question 1.6).** ADR-176 ranks a negative decision over a positive one. This ranks a *human* positive over a *machine* positive when both point at the same content. Both hold; neither implies the other.

| # | Gap | Where |
|---|---|---|
| 6 | Nothing checks manual bindings against slot resolutions | `rendering/service.py:450` |

Source: [[Variant Editor - design interview]] → What Cluster 1 produced, gap 6 (Q1.6).

**Verified against the code 2026-09-27:** `resolve_content_for_module` (`backend/app/rendering/service.py:450`) reads only its own module (`:466-512`), and the render loop calls `render_module` (`:114`) without the variant's manually bound records. The only guard is the CHECK at `backend/app/campaigns/db_models.py:97-100`, which stops one module holding both a record and a slot; nothing compares across modules.

Depends on task-109: when a slot's pick is already bound by hand, the next pick comes from the ranked queue that task builds.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A slot passes over every record placed by hand in the variant, wherever it sits, and fills up to its number from further down
- [x] #2 With the per-send switch on, a recipient is skipped only when no content record shows at all; one hand-picked record is enough to send; typed-in modules do not count
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-09 (interview-review triage, Variant Editor design interview Q1.6): the 'human beats system' rule this task builds had no ADR. ADR-178:118 said the ADR-176 addendum was owed. The adr-author agent is writing that ADR-176 addendum (2026-10-09); build against it, not against the interview text.

2026-10-09: the ADR-176 addendum ('a person's pick outranks the engine's pick of the same content, on a second axis') is written and leaves three points OPEN for the user before this is built.
(1) Hide the slot's module, as the interview says (reusing ADR-086), or take the next ranked pick, as this task's description says (which needs task-109). The sources disagree.
(2) A slot with several records (max_results above 1) where one is bound by hand.
(3) How a slot that stood aside counts under ADR-086's 2026-10-08 'don't send if no slot resolved' option, and what exclusion_reason says.
Line numbers re-checked: resolve_content_for_module is at backend/app/rendering/service.py:646.

2026-10-09, decided by the user (interview review, VE-1.6): when a slot's pick for a recipient is already bound by hand in the variant, the slot takes its NEXT ranked pick (this task's original reading), not the interview's 'hide the module'. That makes task-109 a prerequisite. With no other candidate, the slot resolves nothing and ADR-086's unresolved-slot handling applies. Recorded in the ADR-176 2026-10-09 addendum. Open points 2 (max_results above 1) and 3 (counting) are readings for the final-design pass, not decisions.

2026-10-11, final-design pass with the user. Open point 2 (several picks with a hand-bound record): the hand-bound record is passed over and the slot fills up to its number from further down, like task-109's slot-versus-slot rule. Open point 3 became a correction of the per-send switch: the user said it is for a fully dynamic variant that would show no content; with at least one hand-picked record the email is sent. So with the switch on, a recipient is skipped only when no content record shows at all (no slot pick, none by hand); typed-in modules do not count, or the switch would add nothing to the always-on floor. Recorded in the ADR-176 and ADR-086 addenda of 2026-10-11. Built: frame.hand_bound_ids seeds the send loop's shown set before slots resolve; the skip condition adds not hand_bound; REASON_NO_PICK and the Jinja label say no content record. Verified: tests/test_hand_beats_slot.py (4), 3 mutations killed; full pytest 1911 passed; CI green. No live browser check: the change is send-time behaviour covered by the tests, and the only visible change is the Jinja plan form's label. Commit 5a6645f.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A record placed by hand now outranks a slot's pick of the same record: the slot passes over it and fills from further down. The per-send skip switch now means no content record at all, so one hand-picked record is enough to send (ADR-176 and ADR-086 addenda 2026-10-11). Verified by 4 new tests with all mutations killed, the full suite and CI.
<!-- SECTION:FINAL_SUMMARY:END -->
