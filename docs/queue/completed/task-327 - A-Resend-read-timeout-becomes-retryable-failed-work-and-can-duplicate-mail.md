---
id: TASK-327
title: A Resend read timeout becomes retryable failed work and can duplicate mail
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 14:24'
updated_date: '2026-10-09 16:41'
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

2026-10-09: decided and built (commit 1b4244a; CI green on 2eea13d).

Decisions:
- The user's task-318 rule (never risk a duplicate) applies to a provider timeout.
- Decided with the user: also send Resend an idempotency key. Resend's API reference confirms the Idempotency-Key header (at most 256 characters, remembered 24 hours, "to prevent duplicated emails"); checked 2026-10-09.

Change:
- backend/app/delivery/providers/base.py: SendResult.uncertain, which is provider-neutral.
- backend/app/delivery/providers/resend.py:
  - ConnectError, ConnectTimeout and PoolTimeout (the request was never sent) are a plain, retryable failure;
  - any other httpx.HTTPError (ReadTimeout, WriteTimeout, RemoteProtocolError, ReadError and so on) returns uncertain=True;
  - an Idempotency-Key header is sent when the artifact carries one.
- backend/app/rendering/renderers/base.py: RenderedArtifact.idempotency_key. It is delivery metadata, not part of artifact_hash, so reconstruction and the stored hashes are unaffected.
- backend/app/delivery/service.py:
  - the key is set before the provider call, as "delivery-execution-<id>-<created_at to the microsecond>": stable across retries and practically unique across deployments sharing one Resend account;
  - an uncertain result is recorded as UNCERTAIN with its reason, and every later retry skips it (task-318).

Tests: backend/tests/test_send_timeout.py, 10 tests:
- the three never-left errors are plain failures;
- four maybe-arrived errors are uncertain;
- the header is sent;
- an uncertain result is never resent, and each message has its own key;
- a retried recipient carries the same key.
Mutation check: 6 of 6 caught. The first run missed "a fresh key every attempt", so the same-key-on-retry test was added. Full suite: 1605 passed, and 1608 with Codex's batch.

Also integrated in this push: Codex's test_release_failure_boundaries.py (commit 2eea13d), with three boundary tests for task-325 and task-326.

No live check: it would need a real Resend request timing out, and real email is excluded from testing.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A provider timeout after the request may have reached Resend is now 'uncertain' and never resent; a connection that never opened stays a retryable failure. Every send carries a stable Idempotency-Key, so Resend refuses a second copy for 24 hours. Verified by 10 tests (6/6 mutants caught), the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
