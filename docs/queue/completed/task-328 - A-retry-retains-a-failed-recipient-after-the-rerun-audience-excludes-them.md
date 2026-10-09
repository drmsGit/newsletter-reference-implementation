---
id: TASK-328
title: A retry retains a failed recipient after the rerun audience excludes them
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 14:24'
updated_date: '2026-10-09 16:55'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. Reachable today for a rerun-mode audience send after an execution fails. A recipient removed by the current audience selection can still receive mail on retry.

Evidence checked at HEAD 05088de4 on 2026-10-09: backend/app/delivery/service.py:641-645 resolves current audience IDs, but :660-663 deletes a no-longer-matching execution only when status is created. A failed row remains. The loop at :1115-1144 skips sent/uncertain/left-sending and checks ordinary send-time gates, but does not restrict this failed row to the just-resolved membership set. The provider call at :1244 can therefore mail a still-consenting, addressable person whom the current audience expressly omits.

Deterministic proof: /tmp/tarrow-delivery-premise-proof.py loads actual reconcile_executions_to_audience and full _deliver_claimed bodies through AST with mocked persistence, models, rendering and provider. Give current resolution an empty set and an existing failed execution. Reconciliation deletes nothing; the ordinary delivery gate admits that consenting recipient; the provider is called for test@example.invalid and child ends sent. Trace: resolver []; initial failed; deleted []; provider_calls [test@example.invalid]; terminal sent. Run: backend/venv/bin/python /tmp/tarrow-delivery-premise-proof.py, re-run after source shifted during this session. No DB, network, env file or main/app import. A real database/API reproduction was not performed.

Duplicate check: backlog search audience/retry and full open/completed-task/interview searches. Completed task-318 addresses known success, uncertainty and consent withdrawal on retry. Task-42 addresses channel/purpose and rerun planning; task-90 is a separate audience-override design; task-315's brand sweep is fixed. None tracks retaining failed rows outside re-resolved membership. ADR-176 point 4 governs negative selections and re-resolution. This is a behavior defect, not a question about frozen versus rerun policy. No fix proposed; pre-stage only, no priority or ordinal.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's pre-stage (draft-3, found while preparing the interview questions, docs/queue/docs doc-8) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: reconcile_executions_to_audience deletes an execution no longer in the re-resolved audience only when its status is 'created' (backend/app/delivery/service.py, about :662); a 'failed' row stays, and the retry loop sends it.

2026-10-09, fixed (commit ce7905f). ADR-176 point 4 governs (the audience is re-resolved on every send attempt); no new decision was needed, since the entry describes the existing rule being broken, not a policy question.

What changed: reconcile_executions_to_audience (backend/app/delivery/service.py) now returns the re-resolved member ids, or None when the send has no audience group. Its deletions are unchanged: it still drops only 'created' rows. In _deliver_claimed, the loop checks each remaining execution against that membership. The check runs after the sent / uncertain / sending-to-uncertain skips, so anyone possibly mailed is never relabelled, and before the exclusion stack. A recipient outside the membership is recorded 'excluded' with reason 'audience: no longer in the send's audience' (STAGE_AUDIENCE and REASON_LEFT_AUDIENCE in backend/app/delivery/exclusion.py). The row is kept rather than deleted, so the earlier failed attempt keeps its trace and the detail screen counts it under exclusions_by_stage. The screen lists stages generically, so no frontend change was needed.

Why not delete the failed row instead: it would erase the record of an attempt that did reach the provider. Keeping and re-checking it each run also means someone who rejoins the group before a later retry is sent to.

Found while building: a row that becomes 'sending' kept an earlier exclusion reason. So a rejoiner (or, before this fix too, someone consent-excluded on one run and eligible on the next) ended 'sent' with a stale reason, which exclusions_by_stage then counted. The reason is now cleared when the row is marked 'sending'.

Tests: backend/tests/test_retry_audience.py.
- A failed recipient who left the group is excluded on retry and not mailed, while the stayer is sent.
- Fail, leave, retry (excluded), rejoin, retry: sent once, no reason.

Both failed first (the retry mailed 2 people instead of 1).

Mutation check: all three mutations are caught.
- With the membership check removed, 2 tests fail.
- With reconcile returning None, 2 tests fail.
- Without the reason clear, 1 test fails.

Full suite: 1610 passed, exit 0. Ruff clean. Codex's regression branch had no unpicked commits.

No live browser check: the dev mock provider never fails, so a failed-then-retried send cannot be produced on scratch data without patching code. The tests run the real send path against the dev Postgres.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A retry no longer mails a recipient who left the send's audience after a failed first attempt. Reconciliation (ADR-176 point 4) now returns the re-resolved members. The send loop records any not-yet-final execution outside them as 'excluded' at a new 'audience' stage; the row is kept for its trace and re-checked every run, so a rejoiner is sent to. A row being attempted also drops any stale exclusion reason. Verified by backend/tests/test_retry_audience.py (failed first, all three mutations caught), the full suite (1610 passed), Ruff, and green CI on ce7905f. No live check: the dev mock provider cannot fail on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
