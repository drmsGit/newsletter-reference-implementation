---
id: TASK-328
title: A retry retains a failed recipient after the rerun audience excludes them
status: To Do
assignee: []
created_date: '2026-10-09 14:24'
updated_date: '2026-10-09 14:34'
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
<!-- SECTION:NOTES:END -->
