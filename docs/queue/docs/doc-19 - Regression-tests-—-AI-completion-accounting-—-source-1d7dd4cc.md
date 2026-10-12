---
id: doc-19
title: Regression tests — AI completion accounting — source 1d7dd4cc
type: other
created_date: '2026-10-11 16:01'
updated_date: '2026-10-11 19:57'
---
Source covered: 1d7dd4cc55e9758e792896bdaeaa9508a63585bd, task-345, ADR-144 addenda of 2026-10-09 and 2026-10-11.
Batch commit: 2b74143b82441e3e4d548d3088d55fb75e330e42. Origin push succeeded (exit 0), explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests refspec; git ls-remote verified the same full SHA. Allowed-path restriction checked before commit and push; previous batches preserved.
Added file: backend/tests/test_ai_run_completion_accounting.py.

Strict defects reproduced:
1. test_a_run_without_a_request_records_system_not_a_legacy_unknown: successful requestless run records (None, None) instead of ('system', None); NULL is reserved for legacy unknown actors by the accepted addendum.
2. test_a_run_spanning_a_period_boundary_counts_when_the_provider_answers: a mocked provider returns 17 billable tokens after the period window advances, but the new ledger reports 0. AIRunDB.created_at defaults to PostgreSQL now(), the transaction-start clock; prompt/budget queries start the transaction before the provider answers. A run spanning the reset therefore lands in the earlier period. The test advances period_start only after the pre-call gate and uses PostgreSQL clock_timestamp() as the actual completion boundary, with no real provider call or sleep. The calendar month/quarter/year calculation is covered separately by existing tests.
These are task-345 defects, not task-315 through task-323. No skips, xfails, weakened assertions, or production fixes.

Exact-source managed snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-purpose-integrated/newsletter-reference-implementation, detached at 1d7dd4cc55e9758e792896bdaeaa9508a63585bd. Disposable DB app_test_newsletter_reference_implementation_2435c5, no TEST_DATABASE_URL override, no backend/.env; sequential suites in this checkout, mock adapters and suite real-provider guards. The billable label in the boundary test is paired with a monkeypatched mock adapter, never a real Claude call.

Validation:
- At source 40cc7376538a15346e7084ad1f7f0f767a356217, isolated root: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q backend/tests/test_key_expiry.py backend/tests/test_integrations_api.py --tb=short: 32 passed, exit 0.
- At intended source 1d7dd4cc, isolated root: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q backend/tests/test_ai_run_completion_accounting.py backend/tests/test_ai_budget_period.py --tb=short: 18 passed, 2 failed, exit 1, only the strict defects above.
- Isolated backend: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests --tb=short: 1861 passed, 10 existing skips, 2 failed, exit 1, only the same new tests fail.
- Isolated backend: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache tests/test_ai_run_completion_accounting.py: exit 0.
- git diff --check: exit 0.
- Isolated frontend: node node_modules/vitest/vitest.mjs run: 269 passed across 32 files, exit 0; node node_modules/typescript/bin/tsc -b: exit 0.
- Contract: app.openapi() exported to /private/tmp/ai-completion-openapi.json with DATABASE_URL derived from tests.checkout_database.test_database_url(); node node_modules/openapi-typescript/bin/cli.js /private/tmp/ai-completion-openapi.json -o /private/tmp/ai-completion-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/ai-completion-schema.d.ts: exit 0.
No infrastructure failures. Legacy-data migrations 0046 and 0047 were inspected, not run against legacy data; fresh-schema suite does not prove migration behavior. Parent-source replay would lack the new actor columns and fixture module, so it would fail at collection instead of proving behavior. No production mutation performed.

Persistent branch worktree /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation. Previous tip 5caf6a591b3c92e7836f320e9a031070e845cba3 preserved; production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a. No production history merged. Exact intended-source results above are not validation against that older branch base, which lacks the fixture module and actor columns. Integration pending; strict tests should land with fixes. Backend suite is not green; coverage sufficiency is not claimed.

## Integration verified 2026-10-11

Source 6d35b5847fade5266de30154d565b4e03c1fad52 integrates backend/tests/test_ai_run_completion_accounting.py byte-for-byte from tests batch 2b74143b82441e3e4d548d3088d55fb75e330e42 and fixes both actor and completion-time defects. No pending integration for this batch remains.

In isolated worktree /Users/diedeslembrouck/.codex/worktrees/regression-results-picks/newsletter-reference-implementation pinned to that source, disposable database app_test_newsletter_reference_implementation_99648d, real providers blocked:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_ai_run_completion_accounting.py tests/test_ai_budget_period.py -q: 20 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 1880 passed, 10 existing skips, exit 0 (73.80s).

No infrastructure failures. This confirms intended-source integration, not a green suite on the persistent tests branch's older production base. Legacy migration upgrades remain unverified. Original authorized batch push remains successful; no new test batch needed for this fix.
