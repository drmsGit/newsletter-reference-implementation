---
id: TASK-4
title: >-
  The approval row lock is released by a commit made inside the action it is
  protecting.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 14:37'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P1, and it defeats the guard whose own docstring explains why it must exist.** **The approval row lock is released by a commit made inside the action it is protecting.** `_claim` takes `with_for_update()` on the pending row (`approvals/service.py:162-175`) and `approve` means to hold it across `module.execute` (`:193-214`) — but the action runs on the **same session**, and `send_send_instance` sets the instance to `sending` and commits (`delivery/service.py:391-392`). That commit ends the transaction holding the lock while the pending row still reads `pending`, because `approve` writes its status only after execute returns (`:234-246`). Two approvers can therefore both claim and both enter execute; the second is stopped only by `send_send_instance`'s own status guard — which is precisely the masking `_claim`'s docstring names as the reason for its existence, now happening for real. The first approvable action that commits internally and is not independently idempotent will double-execute. **Fix:** claim by state, not by lock: `UPDATE pending_actions SET status='executing' WHERE id=? AND status='pending' RETURNING id`, run the action, then finalise only the claim this caller won. **Why P1:** concurrent approval is the guarantee the mechanism is sold on, and it is not there. Needs a two-session test where the action commits before returning. Source: `CODE_REVIEW_2026-09-19` P1-01, verified 2026-09-19.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 37, section "Bugs", position 4 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed 2026-09-29 together (commit after 1da074b). Held actions are claimed by a committed conditional pending→executing UPDATE before the action runs, so an action that commits internally can no longer release the guard; reject and expiry use the same conditional move, so a sweep cannot overwrite a decision from a stale read or double the expiry event. New 'executing' status via migrate_0022 (check constraint + widened one-open partial index), recorded in an ADR-142 addendum drafted by the adr-author agent. Verified by a two-thread test where a mid-run-committing action is approved twice and runs once — the original lock-based service fails it — plus stale-read expiry tests the pre-fix body fails; 707 tests pass; 0022 applied to dev through the ADR-181 runner and read back.
<!-- SECTION:FINAL_SUMMARY:END -->
