---
id: TASK-13
title: The expiry sweep claims nothing.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
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
