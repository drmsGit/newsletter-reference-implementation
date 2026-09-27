---
id: TASK-166
title: >-
  `send_send_instance` never consults `result.success` from `provider.send()` —
  `execution.status` is unconditionally set to `"sent"` regardless of the actual
  result (`delivery/service.py:168`), and th…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: bug
ordinal: 503000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `send_send_instance` never consults `result.success` from `provider.send()` — `execution.status` is unconditionally set to `"sent"` regardless of the actual result (`delivery/service.py:168`), and the mock provider always returns `success=True` so this path is never exercised. Distinct from Q3 (that's an exception being raised; this is a returned failure result being ignored). Fix: consult `result.success` when setting status, and log the full result (success/failure/message) for every send attempt, not just failures — small observability fix, useful regardless of provider. Defer the harder part (how to react differently to varied real-provider failure modes/retry semantics) until real providers are integrated — building that against a mock that only ever succeeds would be guesswork. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q6. **Done 2026-07-12** — status is now `"sent"` only if `result.success`, else `"failed"`; added a `message` field to `SendResult` and log the full result per attempt. Also added `logging.basicConfig(level=logging.INFO)` in `main.py` — the app had no logging configuration at all, so this and other `logger.info` calls were previously being silently swallowed.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 561, section "Done", position 30 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
