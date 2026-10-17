---
id: doc-13
title: Regression tests — CI database guard — source ba1e846
type: other
created_date: '2026-10-11 08:59'
updated_date: '2026-10-11 09:00'
---
Source commit: ba1e8461ed141864b3c3c834c2b0ce1818118192.
Associated work: task-349; repair of the CI database guard in the Codex envelope regression batch.
Tests-branch batch commit: 8c637d2a9796400c61cf23ce4c17fd3d0ff989a0. This note is created and read back before staging.
Modified: backend/tests/test_envelope_frame_boundaries.py only.
ADRs: 183 and 194 (point 17 carries forward ADR-193's frozen-frame rule).
No new behavioral tests: preserve all five strict regressions and copy the source commit's proven guard correction onto the persistent tests branch.

Chronological review:
- 779db717e5d77d0ad3e54f0412b1838d3859e6d0 integrated batch 964d51ea7e0490795f40a6540d6f51dfd9aa58f9 unchanged. On the exact commit, five tests pass locally. The original guard fails with a valid CI-style database name.
- 2b734a6bfdd4d7caceb0ba6ea0f1a3d2992f6485 is documentation only: ADR-194 supersedes ADR-193 and preserves the implemented rename and frozen-frame contract. No unrelated future-profile tests added.
- ba1e8461ed141864b3c3c834c2b0ce1818118192 corrects the test harness assertion, without changing behavioral assertions or production code.

Exact source worktree: /Users/diedeslembrouck/.codex/worktrees/regression-envelope-ci/newsletter-reference-implementation.
Backend cwd: that worktree/backend.
Runtime: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python.
Isolation confirmed: backend/.env absent (never read); no incoming TEST_DATABASE_URL. Checkout-derived disposable database app_test_newsletter_reference_implementation_671181 differs from development. CI-style probe uses a separate checkout-specific disposable database app_ci_671181_test, never shared app_ci_test. The probe derives its connection from test_database_url(), replaces only the database name using the checkout-path hash, and asserts it differs from dev_database_url() before invoking pytest. Suites ran sequentially. Provider refusal guard remains active; no real-provider traffic.

Commands/results:
- At 779db717: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_envelope_frame_boundaries.py: 5 passed, exit 0 on derived database.
- At 779db717, same command with TEST_DATABASE_URL derived as described above for app_ci_671181_test: 4 passed, 1 failed, exit 1. Only the database-name assertion fails before migration SQL executes. This is a test-harness defect, not an open product bug or task-315 through task-323 failure.
- At ba1e846, same CI-style command on the same disposable database: 5 passed, exit 0. This demonstrates the correction distinguishes the broken predecessor.
- At ba1e846: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests: 1663 passed, 10 existing skips, exit 0 in 65.67s.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_envelope_frame_boundaries.py: passed, exit 0.
- git diff --check: passed, exit 0.

Guard: assert the engine database equals DATABASE_URL after conftest selects/refuses/rebuilds the test database, and is not DEV_DEFAULT. Conftest already rejects the incoming custom development database before redirecting. The overly narrow "_test_" substring was the defect.

Infrastructure/unverified: actual GitHub CI execution was not inspected; this is a local reproduction with a CI-style name, not a claim of a passing remote CI run. Full local backend suite verified. No frontend or API changes in these commits; prior frontend verification remains separate.
Known-bug failures at intended source: none observed.
Persistent branch parent: 964d51ea7e0490795f40a6540d6f51dfd9aa58f9; production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a. Exact source validation must not be confused with running against the older branch base. No production history merged.
Integration: original envelope batch is integrated in 779db717; the guard correction is already integrated in ba1e846. This branch update preserves the corrected batch for future handoff; no additional main integration is needed for this correction.
Origin push: SUCCEEDED, exit 0. Explicit command: git push origin refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. git ls-remote origin refs/heads/codex/regression-tests confirmed 8c637d2a9796400c61cf23ce4c17fd3d0ff989a0. Before commit and push, branch identity, staged paths, exact diff and diff against previous tip were verified; sole changed file is backend/tests/test_envelope_frame_boundaries.py. No hooks bypassed; persistent branch clean.
