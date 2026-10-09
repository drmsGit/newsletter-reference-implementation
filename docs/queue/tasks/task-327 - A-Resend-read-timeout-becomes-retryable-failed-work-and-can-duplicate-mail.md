---
id: TASK-327
title: A Resend read timeout becomes retryable failed work and can duplicate mail
status: To Do
assignee: []
created_date: '2026-10-09 14:24'
updated_date: '2026-10-09 14:34'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. Reachable today with the shipped Resend adapter. An ambiguous timeout after possible provider acceptance becomes retryable failed work, contrary to completed task-318's never-risk-duplicate decision.

Evidence checked at HEAD 05088de4 on 2026-10-09: backend/app/delivery/providers/resend.py:68-79 posts without an idempotency key, catches httpx.HTTPError including ReadTimeout, and returns SendResult(success=False). backend/app/delivery/service.py:1242-1244 commits sending before calling the adapter, but :1256 changes a false result to failed. The retry skips sent/uncertain/left-sending at :1115/:1121/:1129, not failed. A caught response timeout therefore bypasses the uncertain-outcome guard.

Deterministic proof: /tmp/tarrow-delivery-premise-proof.py loads actual ResendProvider, reconciliation and complete _deliver_claimed function bodies through AST, substituting only imports/annotations and external persistence/render/network boundaries. Mock httpx.post to record a request and raise ReadTimeout. First run: execution failed, parent failed, one request. Retry with a successful mocked response: execution sent, two cumulative requests. Run: backend/venv/bin/python /tmp/tarrow-delivery-premise-proof.py. Re-run against current source after concurrent edits. No application startup, env file, database or actual outbound request. This proves ambiguous classification and replay, not vendor acceptance during a real timeout.

Duplicate check: completed task-318 read through CLI, especially AC #3, decision and final summary. Its uncertainty tests use exceptions escaping provider.send; the shipped adapter catches this one. Open task-81 is broader provider reconciliation, not this adapter/service classification bug. Searches of timeout/uncertain/retry in open/completed tasks and review docs found no accepted item for this path. ADR-100/101/183 govern the adapter/evidence area; task-318 records the specific accepted policy. No fix or new design is proposed. Pre-stage only, no priority or ordinal.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's pre-stage (draft-2, found while preparing the interview questions, docs/queue/docs doc-8) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: backend/app/delivery/providers/resend.py catches httpx.HTTPError, which includes ReadTimeout, around the send and returns SendResult(success=False); backend/app/delivery/service.py:1256 then records 'failed', and a retry resends failed executions. task-318's uncertain marker covers only an exception escaping provider.send. When built, decide whether an ambiguous timeout becomes 'uncertain' (consistent with the user's task-318 decision, never risk a duplicate) and whether Resend's idempotency key should also be sent; a connection error before the request was sent is a genuine failure and stays retryable.
<!-- SECTION:NOTES:END -->
