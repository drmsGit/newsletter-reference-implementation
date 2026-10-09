---
id: doc-8
title: Regression tests — stranded release boundaries — source 05088de
type: other
created_date: '2026-10-09 15:19'
updated_date: '2026-10-09 15:19'
---
Source commit: 05088de4b7b594c378e0770e8962ae3a19322552 (task-326), incorporating task-325's d7a30908b173f1967ed855d033b8bd89111b53ae.
Tests branch batch: 5e9c4032dfc571c82419a5072fa734897333811d on codex/regression-tests. Push to origin succeeded; ls-remote confirmed that exact SHA. Only backend/tests/test_release_failure_boundaries.py changed (96 lines). No production merge, main change, PR, or automatic integration.

Added strict behavioral tests:
- Release rechecks recipient activity after a screen has shown the stranded flag (task-325).
- A caller cannot release another brand's send (task-325).
- Failure after flushing a held request rolls back both records, emits no false success audit, and permits a clean retry (task-326).

Applicable ADRs: ADR-192 and ADR-142. ADR-192 itself was committed just after the task-325 feature; the held-request addenda were committed just after task-326. Those subsequent decision documents were read as context, without changing either feature snapshot.

Exact validation snapshots:
- /Users/diedeslembrouck/.codex/worktrees/regression-stranded-release/newsletter-reference-implementation at d7a30908b173f1967ed855d033b8bd89111b53ae.
- /Users/diedeslembrouck/.codex/worktrees/regression-held-release/newsletter-reference-implementation at 05088de4b7b594c378e0770e8962ae3a19322552 plus the added test file.
Backend Python: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python.
Commands run from each snapshot's backend directory:
- python -m pytest -q tests/test_stranded_send.py: 8 passed at d7a309; 11 passed at 05088de, exit 0.
- python -m pytest -q tests/test_release_failure_boundaries.py tests/test_stranded_send.py: 14 passed at 05088de, exit 0.
- python -m pytest -q tests: d7a309 1582 passed, 10 existing skips; 05088de plus regressions 1588 passed, 10 existing skips. Both actual exit codes 0.
- python -m pytest -q tests/test_release_failure_boundaries.py: 3 passed after mutation proof, exit 0.
From d7a309 frontend: node node_modules/vitest/vitest.mjs run src/screens/Deliveries.test.tsx: 12 passed; node node_modules/vitest/vitest.mjs run: 227 passed in 28 files; node node_modules/typescript/bin/tsc -b: passed. All exit 0.
From 05088de root: backend venv ruff check --no-cache backend/tests/test_release_failure_boundaries.py: passed, exit 0.

Database isolation confirmed: no TEST_DATABASE_URL override; derived disposable databases app_test_newsletter_reference_implementation_48f88d and app_test_newsletter_reference_implementation_2ebe4d differ from the development database and each other. Tests used mock delivery providers; no .env read or real email.

Mutation evidence: temporary external pytest plugin /private/tmp/release_atomicity_mutation.py injected a commit after fail_stuck_requests flushed its records. PYTHONPATH=/private/tmp:. python -m pytest -q -p release_atomicity_mutation tests/test_release_failure_boundaries.py::test_held_request_failure_rolls_back_release_and_allows_a_clean_retry failed on failed versus sending, exit 1. This deliberate mutation failure is proof, not an open production defect. The unchanged regression then passed without the plugin.

Current source failures exposing open bugs: none in this batch. No new failing test assigned to task-315 through task-323. Existing open task-327 through task-329 remain outside this batch's changed-behavior scope.

Infrastructure: initial cached Ruff and non-escalated Backlog creation were denied filesystem writes; no-cache Ruff and authorized escalated CLI succeeded. No remaining blocked checks. OpenAPI contract export/check was not run; frontend typecheck and delivery UI tests passed.

Integration limitation: persistent tests branch retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and all earlier test batches. It does not contain the new release feature or its tests.test_stranded_send helper. This batch was validated against exact source 05088de, not the older tests-branch base. Apply the test commit alongside the feature history; no production history was merged merely to obtain green tests.

Coverage assessment: the release behavior now has passing normal-flow, authorization, stale-state, brand-isolation and transactional-failure tests. This is focused regression coverage, not exhaustive proof of concurrency or crash safety. Review completed through documentation commit 5d1909eb15aa0408357ce78574384562ecc33a7b.
