---
id: doc-14
title: Regression tests — profile stale state — source 00838768
type: other
created_date: '2026-10-11 10:07'
updated_date: '2026-10-11 11:03'
---
Source: 00838768444b63699bba208b1958480c04ef11db (task-350 profiles and task-357 legal footer). First affected commits: a705fdd1f04f9bf4b89d9589377c9a1d0f46d013 (default service) and 79044484d73efb6896d5e94da92a6f69bd59e59f (profile editor).
Tests-branch batch commit: aa7cc036bd78f79525917a1c0f5b30d75f977357. Origin push succeeded (8c637d2 -> aa7cc03); git ls-remote independently confirmed aa7cc036bd78f79525917a1c0f5b30d75f977357 on refs/heads/codex/regression-tests. Only the two allowed test paths changed, matching the validated snapshot byte-for-byte.
Files:
- backend/tests/test_brand_profile_default_state.py
- frontend/src/screens/BrandProfileRefresh.test.tsx
Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-envelope-ci/newsletter-reference-implementation, detached at the exact source.
Disposable database: app_test_newsletter_reference_implementation_671181. backend/.env absent; no .env read, no real provider calls. Conftest provider guard and test fixtures used.

Two strict failures expose unresolved task-350 implementation defects, not mapped to task-315 through task-323:
- test_default_change_after_another_session_changes_the_default: a session holding previously read profiles fails with ux_brand_profiles_one_default_per_brand UniqueViolation after another session changes the default. Row locking does not refresh existing identity-map objects. This is a deterministic stale-session service test, not a threaded HTTP race.
- preserves an unsaved profile field when a background refresh brings a newer version: the editor replaces My unsaved company with Other manager company on query invalidation. No explicit discard was requested.
No production changes, skip/xfail markers, or weaker assertions. These defects have no newly accepted bug tasks; tasks were not modified.

Commands and actual results (run in snapshot backend or frontend as appropriate):
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_brand_profile_default_state.py tests/test_legal_footer.py: exit 1; new backend test failed, all 21 existing legal-footer tests passed.
- node node_modules/vitest/vitest.mjs run src/screens/BrandProfileRefresh.test.tsx: exit 1; new unsaved-input test failed.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests --tb=short: exit 1; 1737 passed, 1 failed, 10 skipped (71.32s). Only the new backend regression failed.
- node node_modules/vitest/vitest.mjs run: exit 1; 260 passed, 1 failed. Only the new unsaved-input regression failed.
- node node_modules/typescript/bin/tsc -b: exit 0. Initial sandbox EPERM writing ignored build-info was resolved by an authorized rerun.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_brand_profile_default_state.py: exit 0.
- git diff --check: exit 0.
- PYTHON_DOTENV_DISABLED=1 Python export of main.app.openapi() with DATABASE_URL set to tests.checkout_database.test_database_url() -> /private/tmp/profile-openapi.json: exit 0, isolated database only.
- node node_modules/openapi-typescript/bin/cli.js /private/tmp/profile-openapi.json -o /private/tmp/profile-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/profile-schema.d.ts: exit 0, generated contract matches.

Chronological source checks:
69b4f64 model/structure 19 passed; a705fdd API/permissions 35 passed; 4c26291 variants/duplication 63 passed; 98fba72 API 24 passed.
7904448 profile/editor tests 23 passed; db6e780 updated Settings routes/profile/editor tests 24 passed.
0944f34, 29071ab, bc00aad, 06da66e, 41e57ee, 429b70f are documentation-only; no empty test commits. bcc55f5 navigation reorder reviewed; existing full frontend checks cover final navigation. 0083876 footer behavior reviewed; 21 targeted footer tests passed.
Coverage is risk-focused and NOT sufficient to claim a passing suite while these strict failures remain.

Persistent tests branch retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and earlier test batches. Tests were validated against source 0083876, not that older base (which lacks brand-profile modules). No production merge into tests branch. Integration must land with the corresponding fixes so main is not made red.
Infrastructure/unverified: remote CI not inspected; old tests-branch base is not validated for these new profile tests. Note creation initially hit a sandbox metadata-lock EPERM; authorized retry succeeded.

9716283c5a49d87f6f6d6e3a76f9932a7be86c3a was subsequently reviewed: documentation-only task-360 clarification; no tests needed. No branch/history rewrite since ba1e846. Both strict regressions are published and awaiting integration together with production fixes.



Integration verified 2026-10-11: 98b6d29c4ff3417e663e069a68a75dcb0aef61f6 integrates both test files from aa7cc036bd78f79525917a1c0f5b30d75f977357 byte-for-byte with production fixes. At that exact isolated source: the strict backend regression passed (1 passed, exit 0); node node_modules/vitest/vitest.mjs run src/screens/BrandProfileRefresh.test.tsx src/screens/BrandProfiles.test.tsx passed all 10 tests (exit 0), including the added original-version If-Match coverage. These two tests no longer await integration.
