---
id: TASK-22
title: >-
  `audit.record()` calls `db.rollback()` on the CALLER's session when it fails —
  including with `commit=False`, which is exactly the case where the caller
  still holds uncommitted work.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 102200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P1 the moment a service writes audit inside a transaction, which approvals already does. Fail-open inverted into fail-destructive.** **`audit.record()` calls `db.rollback()` on the CALLER's session when it fails — including with `commit=False`, which is exactly the case where the caller still holds uncommitted work.** `audit/service.py` never raising is correct and stays: a failure that rolls back a role grant because its *log entry* would not write is the failure mode that gets audit logging switched off in production. But rolling back on the caller's behalf destroys the transaction the swallow was protecting. Both current call sites pass `commit=True`, so it is unreachable **today**; `approvals/service.py` is the shape that reaches it. **Two more from the same function:** the bare `except` means schema drift (a column added without the migration) reads as a log line while the app keeps working; and nothing counts the failures, so "incomplete log" has no number, only a line nobody watches. Source: [[Interview Prep - Channels, Audit]] → B-Q3.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 80, section "Bugs", position 22 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
