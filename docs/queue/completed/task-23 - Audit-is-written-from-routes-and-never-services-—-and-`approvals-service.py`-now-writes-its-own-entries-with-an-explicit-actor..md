---
id: TASK-23
title: >-
  Audit is written from routes and never services — and `approvals/service.py`
  now writes its own entries with an explicit actor.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 20:20'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 102300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. A convention with a stated trigger, and the trigger fired last week.** **Audit is written from routes and never services — and `approvals/service.py` now writes its own entries with an explicit actor.** The split is right and stays: a brand is a property of the data, an actor is a property of the request, and threading the actor through domain signatures would put a request concern in the domain layer for one log. The service's own docstring names this as "the first thing to revisit when it does not hold" — and it does not hold now, because `approval.requested` belongs to a machine that never reached a route handler (it was refused inside a dependency) and `approval.expired` has no request at all. One module is a documented exception; state the pattern for services rather than repeating it. **Independent and quieter:** `record_from_request` reads `request.state` through `getattr` with a `None` default, so renaming a middleware attribute turns every actor into `NULL` silently — fail-open in the single field the table exists for. Source: [[Interview Prep - Channels, Audit]] → B-Q4.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 82, section "Bugs", position 23 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The audit module now states when a service writes an entry (only where no request carries the actor, with the actor passed explicitly — system, integration, or a handed approver), recorded in an ADR-153 addendum drafted by the adr-author agent. record_from_request reads current_user and current_brand strictly, so a renamed middleware attribute raises instead of writing NULL actors. ACTOR_SYSTEM moved into the audit vocabulary; a stale comment fixed. Three tests; the original fails the strict-read one; 761 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
