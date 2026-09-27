---
id: TASK-98
title: >-
  Test and CI gaps named by the 2026-08-07 review — the suite passes and does
  not cover the things that would hurt.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 205100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Test and CI gaps named by the 2026-08-07 review — the suite passes and does not cover the things that would hurt.** 141 tests pass locally, but the reviewer could not collect four modules at all in a clean runtime (`test_ai_subject_task`, `test_auth`, `test_overrides`, `test_signals`) because `app.database` **creates a PostgreSQL engine at import time**, so importing the app requires a live driver and server. That is the same root as the isolated-test-DB Needs-ADR item below, seen from outside: the project is not testable in a fresh container. **Missing tests, ranked by what they would have caught:** (1) **send-time consent revocation** — opt in, prepare a `freeze` send, opt out, trigger, assert the provider is never called; this fails today and is the P0. (2) **Parent send-status aggregation** — all-succeed, all-fail, mixed; all three currently report `sent`. (3) **Brand-scoped permissions** — Manager on Brand A plus Viewer on Brand B must be denied a Manager write on B. (4) **API authentication** — no credential 401, wrong scope 403, scoped credential succeeds. (5) **Webhook fail-closed** with the secret unset. (6) **Exact click attribution** — two content records, two tracked links, click the second, assert only the second gets the contribution. (7) **Concurrent trigger idempotency** — two sessions triggering one send instance, only one submits; the row-lock design looks right but deserves a real Postgres integration test rather than reasoning. (8) **Snapshot write failure** leaves no usable row. **Snapshot immutability tests deliberately come after** the artifact boundary is decided, since the current behaviour is what is in dispute. **Cheap CI gates worth adding:** a clean-container `pip install -r requirements.txt && pytest` (which would have caught `httpx2` immediately), plus ruff, mypy, bandit, pip-audit, and **gitleaks or an equivalent secret scanner** — the last one because the reviewed archive shipped real provider credentials despite `.env` being gitignored. **Three performance smoke tests** are also suggested, tracking **query count as well as duration**, since runtime alone hides the per-recipient query/commit pattern that causes the slowdown. Source: code review 2026-08-07, TESTS.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 277, section "Features", position 51 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
