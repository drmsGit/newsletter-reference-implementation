---
id: TASK-14
title: >-
  The status transition is committed before several fallible preflight steps,
  and outside the handler that would undo it.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 19:07'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 101400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. A send can be permanently stuck in `sending` without anything having been sent.** **The status transition is committed before several fallible preflight steps, and outside the handler that would undo it.** `send_send_instance` commits `status='sending'` at `delivery/service.py:391-392`; the `try` whose handler marks the parent `failed` does not begin until `:508`. In between sits provider construction and capability validation (`:432-438`, `providers/factory.py:28-35`), which raises `ValueError` for an unsupported provider or an unsupported channel. If it does, the instance stays committed as `sending`, every later attempt is refused by the status guard (`:386-389`), and there is no route back. Through approvals it reads worse: `send_fire` treats a `ValueError` as a clean refusal (`approvals/actions/send_fire.py:143-149`), so the request is recorded `failed` while the send is wedged `sending` forever. **Fix:** do all non-mutating validation before the claim commit, or put everything after the claim inside the failure handler so every post-claim exception transitions the send out of `sending`. Source: `CODE_REVIEW_2026-09-19` P2-02, verified 2026-09-19.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 64, section "Bugs", position 14 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed both ways the entry named. Read-only preflight (snapshot, provider, channel) now runs before the sending claim, so a refused send keeps its status and is retryable; everything after the claim is one helper wrapped in a handler that catches any exception, rolls back and marks the send failed (retryable) instead of stranding it in sending. Verified by three tests — including a real database error past the claim, so the rollback is actually exercised — that the original function fails; two narrower handler mutations also caught. 733 tests pass. Known and unchanged: a scheduled send refused before the claim stays scheduled and is retried each scheduler tick, as a required-field refusal already was.
<!-- SECTION:FINAL_SUMMARY:END -->
