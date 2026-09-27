---
id: TASK-193
title: Webhook signature verification fails open when the secret is absent.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 505700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1, security.** **Webhook signature verification fails open when the secret is absent.** `verify_signature()` logs a warning and returns `True` when `RESEND_WEBHOOK_SECRET` is unset (`providers/adapters/resend.py:65-72`). A configuration mistake turns a public endpoint into unauthenticated event ingestion: forged bounces and complaints reach the suppression logic, forged clicks corrupt affinity signals. **Fix:** fail closed. A development bypass must be a deliberate flag, never the *absence* of configuration — the same lesson as the AI adapter's dev-mode heuristic, which inferred "development" from a missing key and duly sent a live email. Source: code review 2026-08-07 P1-05. **DONE 2026-09-13** in `c2c9276` — `verify_signature()` now logs an error and returns `False` when `RESEND_WEBHOOK_SECRET` is unset, with `tests/test_provider_webhook_signature.py` covering both directions. **The marker was stale for most of a day**, and I relayed this entry to the user as still-open while scoping gate 3 — the `adr-author` run caught it by reading the code instead of the entry. Exactly the failure HANDOFF's "verify before trusting a status claim in this repo" section exists for, committed by the person who wrote that section.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 617, section "Done", position 57 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
