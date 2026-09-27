---
id: TASK-165
title: >-
  `send_send_instance` (`delivery/service.py:160-173`) only calls `db.commit()`
  once, at the very end of the send loop — if `provider.send()` raises mid-batch
  (e.g. execution 5 of 100), executions 1-4…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 502900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `send_send_instance` (`delivery/service.py:160-173`) only calls `db.commit()` once, at the very end of the send loop — if `provider.send()` raises mid-batch (e.g. execution 5 of 100), executions 1-4 were actually sent by the provider but never get their `"sent"` status persisted, since the exception aborts the function before the single end-of-loop commit. Keeping "stop the batch on a failure" as the safe default is correct (provider-dependent whether skip-and-continue would even be safe) — but whatever succeeded before the stop must still be recorded accurately. Fix: commit incrementally (or otherwise ensure completed executions are persisted) so the DB never claims an email was never sent when it actually was, independent of retry/skip policy. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q3. **Done 2026-07-12** — commits after each execution in the loop instead of once at the end.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 559, section "Done", position 29 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
