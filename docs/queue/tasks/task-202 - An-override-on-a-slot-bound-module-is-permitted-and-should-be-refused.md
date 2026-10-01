---
id: TASK-202
title: An override on a slot-bound module is permitted and should be refused
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
