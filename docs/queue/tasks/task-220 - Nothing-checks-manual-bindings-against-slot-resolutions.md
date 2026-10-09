---
id: TASK-220
title: Nothing checks manual bindings against slot resolutions
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-09 18:20'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-09 (interview-review triage, Variant Editor design interview Q1.6): the 'human beats system' rule this task builds had no ADR. ADR-178:118 said the ADR-176 addendum was owed. The adr-author agent is writing that ADR-176 addendum (2026-10-09); build against it, not against the interview text.

2026-10-09: the ADR-176 addendum ('a person's pick outranks the engine's pick of the same content, on a second axis') is written and leaves three points OPEN for the user before this is built.
(1) Hide the slot's module, as the interview says (reusing ADR-086), or take the next ranked pick, as this task's description says (which needs task-109). The sources disagree.
(2) A slot with several records (max_results above 1) where one is bound by hand.
(3) How a slot that stood aside counts under ADR-086's 2026-10-08 'don't send if no slot resolved' option, and what exclusion_reason says.
Line numbers re-checked: resolve_content_for_module is at backend/app/rendering/service.py:646.
<!-- SECTION:NOTES:END -->
