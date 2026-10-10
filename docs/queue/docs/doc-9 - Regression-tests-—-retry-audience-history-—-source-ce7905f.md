---
id: doc-9
title: Regression tests — retry audience history — source ce7905f
type: other
created_date: '2026-10-09 17:18'
updated_date: '2026-10-09 20:22'
---
Source commit covered: ce7905f82a12ede9534150814b9db87db7a3f853 (task-328).
Tests-branch batch commit: 35b31c87ab9f5e8d2624f5e081b01c3ee2978feb.
Origin push succeeded to refs/heads/codex/regression-tests only; ls-remote confirmed the full batch SHA. Main was not changed, merged, or pushed; no PR.

Added file: backend/tests/test_retry_audience_history.py (64 lines, three parameterized cases).
Invariants: leaving then rejoining an audience never resends a known sent, already uncertain, or interrupted sending execution. Its delivery status, provider message id, and uncertainty evidence are retained; only a definitely retryable companion is attempted on each run.
ADRs read in the snapshot: ADR-176 (current audiences) and ADR-183 (delivery evidence). Relevant repository instructions were read; no production/configuration/ADR changes.

Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-consent-fixture/newsletter-reference-implementation, detached at exact source ce7905f plus the added tests.
Python executable: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python.
From its backend directory:
- python -m pytest -q tests/test_retry_audience.py tests/test_retry_audience_history.py tests/test_release_failure_boundaries.py: 8 passed, exit 0.
- python -m pytest -q tests: 1603 passed, 10 existing skips, exit 0.
From root:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_retry_audience_history.py: passed, exit 0.
Database derivation checked before execution: no TEST_DATABASE_URL override; app_test_newsletter_reference_implementation_da5dc3 is disposable, differs from development and other running suites. Mock providers only; no .env reads or real email.

Mutation proof: temporary external /private/tmp/audience_history_mutation.py removed the runtime uncertain-execution skip, leaving production files unchanged. From backend, PYTHONPATH=/private/tmp:. python -m pytest -q -p audience_history_mutation 'tests/test_retry_audience_history.py::test_leaving_and_rejoining_never_replays_a_known_or_possible_delivery[uncertain-uncertain]' failed on preservation of uncertain status, exit 1. The subsequent normal full suite passed. This deliberate mutation failure is not an open source bug. The initial one-recipient sent fixture encountered the correct already-sent guard; it was corrected to keep a second recipient retryable, preserving all evidence assertions.

Failures exposing open bugs: none in this batch. No new task-315 through task-323 failures. No skips or expected failures introduced.
Infrastructure/unverified: no infrastructure-blocked checks remain. The persistent tests branch still has production base 28aa4e88f4846768a18fd81b66949f959cd3b38a; it lacks this source's release/audience feature helpers. Results are against ce7905f, not that older branch base. Earlier test batches preserved; no production changes merged. Integrate this test commit with task-328's source history after review.

Other source commits reviewed chronologically:
- 1b4244a10770acc5ca6a909d00f7107f5783e5b5 task-327: existing tests adequately cover safe connection failures, uncertain late network failures, stable/unique idempotency keys, and no uncertain resend. Exact snapshot /Users/diedeslembrouck/.codex/worktrees/regression-new-batches-integrated/newsletter-reference-implementation. Its disposable database app_test_newsletter_reference_implementation_f659ff checked separately. From backend python -m pytest -q tests/test_send_timeout.py: 10 passed; python -m pytest -q tests: 1595 passed, 10 existing skips; actual exit 0. No additional tests needed for that commit.
- 2eea13dc3b7e95e773b3e3051bbf11b0d80fd6ea: integrates prior 5e9c403 release tests, exact file diff unchanged; the three tests pass in ce7905f's targeted and full suite.
- 7012d3f2cf02b1a4079ac417c38631e6299fff29: documentation only, reviewed, no test additions.
- ce7905f82a12ede9534150814b9db87db7a3f853: reviewed/tested, this published batch.
- 70db6fc7937e2bd094e3af04953e006353506089: documentation only, reviewed, no test additions.
- 7a56adc30c11ae25c1e805c6411929fbb54f11f4 task-329: six existing editor tests cover dirty/clean refresh, ordinary save, both conflict choices, and catalogue handoff. Exact snapshot /Users/diedeslembrouck/.codex/worktrees/regression-envelope/newsletter-reference-implementation. From frontend node node_modules/vitest/vitest.mjs run: 233 passed in 29 files; node node_modules/typescript/bin/tsc -b: passed, process exit 0. Existing shared dependencies were linked read-only; no installation changed. No added frontend tests needed.
- 803cdbc861a8d27478609b7609d91d82d589add3: documentation only, reviewed, no test additions.

No history rewrite detected. Last checked SHA: 803cdbc861a8d27478609b7609d91d82d589add3.
Coverage assessment: focused changed-behavior coverage passes, including the new audience/history interaction. This does not claim exhaustive provider or concurrency proof. Batch pending Claude's review/integration.



## Integration verification — 2026-10-09
Claude integrated batch 35b31c87ab9f5e8d2624f5e081b01c3ee2978feb as source commit 860856473d062dce92f2f82b40f9958d1381c6d8. Exact test-file diff is unchanged. Tested in /Users/diedeslembrouck/.codex/worktrees/regression-new-batches-integrated/newsletter-reference-implementation, detached at that integration SHA. Confirmed no TEST_DATABASE_URL override and disposable database app_test_newsletter_reference_implementation_f659ff, distinct from development; mock providers only.
From snapshot backend, /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_retry_audience_history.py: 3 passed, exit 0. Same executable with -m pytest -q tests: 1603 passed, 10 existing skips, exit 0. No new source defects or coverage gaps; no new tests or batch commits needed. Integration is complete and verified.
Per-commit ledger: 860856473d062dce92f2f82b40f9958d1381c6d8 reviewed/tested as above; c023822016892c4d14721888ca5fb57a5fd96b21 reviewed, documentation/ADR addendum only, no executable changes or tests required. No history rewrite. Last checked SHA: c023822016892c4d14721888ca5fb57a5fd96b21.
