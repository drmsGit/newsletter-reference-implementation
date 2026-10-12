---
id: doc-17
title: Regression tests — zero unattended ceiling — source 9a66286b
type: other
created_date: '2026-10-11 12:08'
updated_date: '2026-10-11 12:57'
---
Source: 9a66286bf7e565d55b71ddd6c63b468d76b84dce (task-341), governed by ADR-166's 2026-10-11 addendum: 0 means every send requires approval.
Batch commit: e380c6452d064682e473b74e26c6e72413f0b835. Origin push succeeded, exit 0, using only refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. git ls-remote verified the same full SHA. Allowed-path restriction confirmed before commit and push; prior batches preserved.
Added file: backend/tests/test_unattended_empty_due.py.
Invariant: an integration with ceiling 0 must hold an empty due send; repeated sweeps must retain one pending action, report it held, and leave it scheduled without firing.

Defect reproduced: process_due_scheduled_sends uses size > ceiling, so zero recipients at ceiling 0 bypass the hold. The strict test fails at the first held-list assertion; subsequent repeat/deduplication assertions remain unverified because it fails there. Existing test_unattended_ceiling covers an empty direct fire but misses the batch route. Associated task-341, not task-315 through task-323. No production fix or assertion weakening.

Exact validation snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-transactional/newsletter-reference-implementation detached at 9a66286bf7e565d55b71ddd6c63b468d76b84dce. Its disposable database app_test_newsletter_reference_implementation_a2c648 is separate from development and other suites; tests ran sequentially within that checkout, using mock providers. No .env read or shared dependency installation edits.

Backend commands (cwd isolated backend):
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_unattended_empty_due.py tests/test_unattended_ceiling.py tests/test_integrations_api.py tests/test_process_due_brand.py --tb=short: 38 passed, 1 failed, exit 1; failure is the new zero-ceiling test.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests --tb=short: 1807 passed, 10 existing skips, 3 failed, exit 1. Failures: the new zero-ceiling test and both transactional rule tests from batch c0cd3bf. Session-read test passes.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache tests/test_unattended_empty_due.py: exit 0.
- git diff --check: exit 0.

Frontend (cwd isolated frontend): node node_modules/vitest/vitest.mjs run: 267 passed in 32 files, exit 0. node node_modules/typescript/bin/tsc -b: exit 0 on retry allowing the ignored isolated build-info cache.
Contract: app.openapi() exported to /private/tmp/ceiling-openapi.json with DATABASE_URL derived from tests.checkout_database.test_database_url(); node node_modules/openapi-typescript/bin/cli.js /private/tmp/ceiling-openapi.json -o /private/tmp/ceiling-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/ceiling-schema.d.ts: exit 0.

Infrastructure: initial Ruff cache write, TypeScript build-info write, and Backlog lock creation were denied by sandbox; Ruff succeeded without cache, TypeScript and Backlog succeeded with authorized isolation permissions. No remaining infrastructure blocker. Migration 0045 against legacy data was reviewed but not executed; the suite builds fresh schema and does not prove the migration.

Tests branch worktree: /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation, previous tip c0cd3bf75f3bbadf041203894f300ef91f504e1e preserved. Production base stays 28aa4e88f4846768a18fd81b66949f959cd3b38a; no production history merged. Source fixture test_unattended_ceiling is absent from that older base; validation above is against intended source, not that branch base. Integration pending and strict failing test should land with its fix. No passing-suite or final-sufficiency claim.

Integration verified 2026-10-11: source 5e39bfd65a2096f8f95ae385b18353e6e4c8908f contains the published test byte-for-byte with the zero-ceiling batch fix. Isolated worktree /Users/diedeslembrouck/.codex/worktrees/regression-session-lengths/newsletter-reference-implementation, disposable DB app_test_newsletter_reference_implementation_c357c2. PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q backend/tests/test_unattended_empty_due.py backend/tests/test_unattended_ceiling.py --tb=short: 14 passed, exit 0. Repeated sweeps and one-pending-action assertion now pass.
