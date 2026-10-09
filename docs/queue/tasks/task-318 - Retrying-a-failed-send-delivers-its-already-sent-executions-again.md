---
id: TASK-318
title: Retrying a failed send delivers its already-sent executions again
status: To Do
assignee: []
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 08:23'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. A routine retry after a mid-batch failure sends duplicate mail and replaces evidence of the original delivery. Reachable today.

Evidence: backend/app/delivery/service.py:814 rejects only sending/sent parents. An exception marks the parent failed at 899-915, allowing retry. _deliver_claimed selects all child executions at 960-966 with no state restriction; it calls the provider at 1106 and commits each result at 1135-1138.

Reproduction: create a two-recipient mock send; let the provider succeed for the first recipient and raise for the second. The first execution is durably sent and the parent failed. Retry with a succeeding provider: the first recipient is sent again and its provider message ID/delivery record is overwritten. Reproduced in the first review stage.

The delivery record is the as-sent evidence (ADR-183), and a known committed success must not be replayed as unfinished work. Resume only eligible unfinished executions and preserve committed delivery identity/history; separately reconcile genuinely uncertain provider outcomes.

Related: task-81 concerns provider-side partial-failure reconciliation and task-124 broader concurrency. This case needs no reconciliation: the success is already known locally. Completed task-14 made the failed parent retryable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A retry after a committed success followed by an exception never calls the provider again for that successful execution.
- [ ] #2 Successful executions retain their original provider ID and delivery record through retries.
- [ ] #3 The retry policy distinguishes unfinished work from known success and uncertain provider outcomes.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-3) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: _deliver_claimed (backend/app/delivery/service.py:960-966) selects every execution of the send instance, and the loop at :1016 skips only exclusions, never an execution already sent.
<!-- SECTION:NOTES:END -->
