---
id: TASK-13
title: The expiry sweep claims nothing.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 14:37'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 101300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2, the same defect family as the approval lock above and best fixed in one pass with it.** **The expiry sweep claims nothing.** `expire_due_pending_actions` selects every due row with no lock (`approvals/service.py:310-325`) and `_mark_expired` re-checks no status, takes no lock and commits unconditionally (`:297-307`). Two overlapping sweeps both emit `approval.expired` for the same row; worse, a sweep can read a pending row, an approver can decide it, and the sweep can then commit `status='expired'` over the decision from its stale ORM object — a request that was approved, executed and mailed, recorded as having lapsed. The docstring's "idempotent, and safe to run twice" is true sequentially and not concurrently, which is the distinction that matters once it runs on cron. **Fix:** `SELECT … FOR UPDATE SKIP LOCKED` plus a status re-check, or the same conditional `UPDATE … WHERE status='pending' RETURNING id` used for the approve claim; emit the audit event only for rows this worker actually transitioned. Source: `CODE_REVIEW_2026-09-19` P2-01, verified 2026-09-19.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 62, section "Bugs", position 13 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed 2026-09-29 together (commit after 1da074b). Held actions are claimed by a committed conditional pending→executing UPDATE before the action runs, so an action that commits internally can no longer release the guard; reject and expiry use the same conditional move, so a sweep cannot overwrite a decision from a stale read or double the expiry event. New 'executing' status via migrate_0022 (check constraint + widened one-open partial index), recorded in an ADR-142 addendum drafted by the adr-author agent. Verified by a two-thread test where a mid-run-committing action is approved twice and runs once — the original lock-based service fails it — plus stale-read expiry tests the pre-fix body fails; 707 tests pass; 0022 applied to dev through the ADR-181 runner and read back.
<!-- SECTION:FINAL_SUMMARY:END -->
