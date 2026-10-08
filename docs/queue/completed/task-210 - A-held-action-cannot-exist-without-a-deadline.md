---
id: TASK-210
title: A held action cannot exist without a deadline
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-08 18:33'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200420
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **A held action cannot exist without a deadline** (Q7). `expires_at` is `nullable=False` and `default_ttl_seconds: int` is not optional, so "content review does not expire" is a schema change plus a hand-written migration, and every comparison must then read null as *never expires* rather than *expired*. Touches [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4.

Source: [[Manager Workflow - design interview]] → What Cluster 1 produced, gap 8 (Q1.7).

**Verified against the code 2026-09-27:** `expires_at` is `nullable=False` at `backend/app/approvals/db_models.py:94`; `default_ttl_seconds: int` at `backend/app/approvals/actions/base.py:58`; the service always sets `now() + ttl` (`backend/app/approvals/service.py:115,126`); `expires_at: datetime` is non-optional in `backend/app/approvals/models.py:30`. `backend/app/approvals/service.py:76` already handles `expires_at is None` defensively.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An action type may declare no deadline; its requests are held with none, read as pending, are never swept, and can be approved at any time
- [x] #2 A module that says nothing about a deadline is still refused
- [x] #3 The badge counts such a request, and the inbox and detail say No deadline
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Built 2026-10-08, commit 45311f4. Already decided, nothing asked: ADR-142's addendum of 2026-09-24 and Manager Workflow interview Q1.7 (the deadline belongs to the action type and may be absent; null reads as never, not as already).

Verified first: the entry was still true (expires_at NOT NULL, default_ttl_seconds int, request_approval always computed now() + ttl). Most readers already treated null as never (is_expired returns False, the inbox's pending clause and _status_clause have or_(is_(None), ...)); SQL comparisons against null are false, which is safe for "is it due" (the sweep, due_count, the lapsed clause) and wrong for "is it open": pending_count, the nav badge, read only expires_at > now() and would have hidden such a request - fixed.

Changes: backend/app/approvals/actions/base.py default_ttl_seconds: int | None, still required (None is a declaration, never an omission); service.request_approval stores no deadline when the type declares none; pending_count counts it; models.PendingActionRow.expires_at optional; db_models nullable with migration 0039; frontend/src/screens/Approvals.tsx deadline() - "No deadline" in the inbox and ApprovalDetail.tsx. The Jinja inbox already showed a dash for none.

Tests: tests/test_approvals.py +6 with a planted action declaring none (held without one, pending a decade later, in the inbox and the badge, never swept, approvable, the route answers null, a declaration that omits the field still refused); Approvals.test.tsx +1. 4 mutants, all killed. Backend 1476, client 224, build, schema check and types clean.

Live check 2026-10-08: one scratch held request with no deadline written directly (summary zz-scratch task-210, no action type uses none yet): the React inbox listed it with Expires "No deadline", the detail showed status pending and "No deadline", pending_count counted it, the sweep left it; deleted afterwards.

Unblocks task-206 (content readiness, the first action type with no deadline).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An action type can now declare that its requests have no deadline (ADR-142's 2026-09-24 addendum): such a request is held without one, stays pending, is never expired by the sweep, can be approved whenever, counts in the badge, and the screens say No deadline. A module that says nothing is still refused. Verified by 7 tests (4 mutants killed), the full suites, and a scratch request seen in the inbox and detail. It is the groundwork for task-206.
<!-- SECTION:FINAL_SUMMARY:END -->
