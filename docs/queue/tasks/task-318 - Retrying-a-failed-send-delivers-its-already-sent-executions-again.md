---
id: TASK-318
title: Retrying a failed send delivers its already-sent executions again
status: Blocked
assignee: []
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 11:14'
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
- [x] #1 A retry after a committed success followed by an exception never calls the provider again for that successful execution.
- [x] #2 Successful executions retain their original provider ID and delivery record through retries.
- [ ] #3 The retry policy distinguishes unfinished work from known success and uncertain provider outcomes.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-3) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: _deliver_claimed (backend/app/delivery/service.py:960-966) selects every execution of the send instance, and the loop at :1016 skips only exclusions, never an execution already sent.

2026-10-09: AC #1 and #2 fixed (commit a0d06e6; CI green). AC #3 is blocked on a user decision.

Change: the send loop in _deliver_claimed (backend/app/delivery/service.py) skips an execution whose status is already "sent", as its first step, before the exclusion check. A known success is never sent again, and its provider_message_id and delivery_record (ADR-183) are never rewritten. Putting the skip before the exclusion check matters: otherwise a person opted out since the first run would be relabelled "excluded", rewriting what was sent. The parent's counts still include the skipped successes, because the count loop reads every execution.

Tests:
- backend/tests/test_send_retry.py (mine, reusing test_render_skip's world fixture): the retry mails only the unfinished recipient and keeps the original message id and record, and the parent ends "sent" with sent_count 2. Also: a person sent to and then opted out stays "sent". Both failed before the fix (2 mailed, and "excluded" overwrote "sent"). Mutation check: removing the skip fails both.
- backend/tests/test_send_retry_consent_regression.py (Codex, commit 93c0ea3, cherry-picked from codex/regression-tests after review): the unfinished recipient opts out before the retry, the retry mails nobody, the evidence is kept, and the counts are 1 sent and 1 excluded.

Blocked, AC #3 (uncertain provider outcomes): when provider.send raises, the execution stays "created". Nothing distinguishes "never attempted" from "the provider may have sent before the error" (a timeout after acceptance). Telling them apart needs a marker committed before each provider call, for example status "sending", one more commit per recipient. It also needs a policy for what a retry does with such an execution:
- skip it: no duplicate, but the recipient may never get the mail;
- resend it: never missed, but maybe a duplicate;
- hold the send for reconciliation, which is task-81 (provider-side partial-failure reconciliation).
This is the user's decision.

2026-10-09, decided by the user for AC #3: an execution whose provider outcome is uncertain is SKIPPED on retry, never resent. Reason (user): a duplicate send must not be risked. If many recipients end up 'not delivered', they are checked and resent by hand. To build:
- mark each execution just before the provider call, committed, so a crash leaves it distinguishable from 'never attempted';
- a retry skips it and records it under a distinct status, visible and filterable in the send's executions list.
The manual resend path that exists today: paste those people into an audience group and plan a new send to it. Nothing automates that, by decision. Not built yet; the task stays Blocked until the build.
<!-- SECTION:NOTES:END -->
