---
id: TASK-98
title: >-
  Test and CI gaps named by the 2026-08-07 review — the suite passes and does
  not cover the things that would hurt.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 20:55'
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

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every gap the 2026-08-07 review named is covered by a test, handed to a named task, or decided
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 277, section "Features", position 51 in that section (top = do next). The description is the original entry, verbatim.

Closed 2026-10-08 (pre-review list). Re-checked against today's ~1500 tests (Explore sweep) before writing anything:
- Not testable in a fresh container: fixed by CI (task-105, ADR-190): a clean venv from the hashed locks passes the suite on GitHub.
- Covered already: 1 send-time consent revocation (tests/test_consent_gates.py:729), 3 brand-scoped permissions (tests/test_brand_scoping.py:644), 4 API authentication (tests/test_api_guard.py: 401, 403, 200/201), 5 webhook fail-closed at the function (tests/test_provider_webhook_signature.py:32).
- Added, commit 7efc27a (no product change; each behaviour was right and untested; 6 mutants killed, including removing only the row lock):
  1. the provider is never handed an opted-out recipient;
  2. every provider failure reports the send failed, some report partial_failed;
  5. at the route, a well-signed event is refused while the secret is unset;
  6. two records, two links: clicking the second credits only the second (it turned out to be a seeded record the slot picked per recipient, credited with all its own categories and nothing of the first);
  7. two threads with their own sessions trigger one send: one sends, one is refused, the provider is called once;
  8. a snapshot whose frame cannot be built or rendered leaves no row.
- CI gates: ruff, pip-audit and gitleaks are in CI (task-105). mypy stays later and gradual (task-105). bandit: decided with the user, not a separate tool and not report-only; nine of Ruff's bandit rules block (ADR-190 addendum 2026-10-08, commit f4eecb9).
- The three query-count performance smoke tests: handed to task-106 (benchmark), noted there.
Found on the way and filed: task-303 (the webhook accepts a signed event of any age - replay; first in the queue as a bug), task-304 (the consent tests' zero-module fallback snapshot would be skipped by task-228's floor).
Suites: 1504 locally; CI green (1503 passed, 1 skipped by design).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The August review's test gaps are closed: four were already covered by the suite that grew since, six partial ones got the missing tests (provider never called for an opted-out person, failed and partly failed send status, the webhook route failing closed, second-link click attribution, two simultaneous triggers sending once, a failed snapshot leaving no row), the CI gates exist (task-105) with bandit's serious checks blocking through Ruff, and the query-count smoke tests went to task-106. Two findings were filed: task-303 (webhook replay) and task-304 (a fragile test fixture).
<!-- SECTION:FINAL_SUMMARY:END -->
