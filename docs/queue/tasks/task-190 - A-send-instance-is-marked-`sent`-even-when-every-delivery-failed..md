---
id: TASK-190
title: A send instance is marked `sent` even when every delivery failed.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 505400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1.** **A send instance is marked `sent` even when every delivery failed.** Each execution gets `sent`/`failed` correctly from the provider result, then `send_instance.status = "sent"` runs unconditionally after the loop (`delivery/service.py:433`). 100 of 100 failures still yields a parent status of `sent`; only an exception escaping the loop marks it `failed`, and provider failures return `SendResult(success=False)` rather than raising. **Fix:** derive the parent from its children — `sent` / `partial_failed` / `failed` — and persist the failure count so monitoring, retries and the audit trail stop lying. Source: code review 2026-08-07 P1-03. **DONE 2026-09-13.** Parent status is now derived from the child executions — `sent` / `partial_failed` / `failed` — with `sent_count`, `failed_count` and `excluded_count` persisted on `SendInstanceDB` (migration 0003, additive; existing rows deliberately not backfilled, since a computed number would be indistinguishable from a recorded one). **One case this entry predates:** the ADR-163 §7 exclusion stack means a send can now end with every recipient excluded — nothing sent, nothing failed. Decided 2026-09-13 to give that its own status, **`no_recipients`**, rather than round it to a neighbour: `sent` would show green for a send that delivered nothing, which is precisely the lie this item exists to stop, and `failed` would invite retrying something that worked correctly. `excluded_count` is kept apart from `failed_count` for the same reason — an exclusion is the stack working, not a delivery problem.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 611, section "Done", position 54 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
