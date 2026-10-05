---
id: TASK-284
title: Decision slots pick only machine-ready records ready for their channel
status: To Do
assignee: []
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 18:14'
labels:
  - backend
dependencies:
  - TASK-283
type: feature
ordinal: 200120
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-282 design session (2026-10-05). Recorded in the ADR-174 addendum 2026-10-05 (point 2) and the ADR-179 addendum 2026-10-05 (point 3). Depends on the storage task.

**Today** `candidate_query` (`backend/app/decision/strategies/base.py:176-214`) filters on `status == "active"` (around line 203), the sending brand and `category_ids` only. The candidate count (`backend/app/campaigns/service.py`, `slot_candidate_count`, and `GET /campaigns/decision-slots/{id}/candidates`) uses the same query.

**Decided:** a record is a candidate only if it is machine ready AND marked ready for the slot's channel, the channel of the slot's variant. Put both conditions in `candidate_query`, so the count and every strategy agree. `explain_candidates` (if present) should say why a record was left out ("not machine ready" or "not ready for push").

**The demo seed** (`backend/scripts/seed_demo_data.py`, `create_demo_content_if_empty`) marks its slot content machine ready and ready for email, so the demo still resolves.

**Tests:**
- each condition excludes a record on its own;
- the email backfill keeps today's dev slots resolving;
- a push slot finds nothing until a person marks push readiness.

**What could break:** every test that builds slot candidates without these marks. Their fixtures need the marks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 candidate_query requires machine ready and readiness for the slot's channel; the candidate count agrees
- [ ] #2 The demo seed and existing slots keep resolving; a push slot finds nothing until push readiness is marked
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
OPEN, ask the user before building (raised 2026-10-05 by the ADR-174 addendum work): ADR-174 Notes (around line 86) leaves open whether a record marked ready but missing a required field is excluded from slot candidacy. As designed, the rule reads the two marks only, so such a record stays a candidate. The send-time required-field check skips slot-bound modules on purpose (backend/app/rendering/frame.py, around 257-258), on the reasoning that a slot pick missing a field should skip that recipient, not block the send. That per-recipient skip is task-228 and is not built. Put the question to the user, with a recommendation, before building this task.
<!-- SECTION:NOTES:END -->
