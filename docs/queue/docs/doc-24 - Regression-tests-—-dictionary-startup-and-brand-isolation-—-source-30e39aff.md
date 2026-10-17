---
id: doc-24
title: Regression tests — dictionary startup and brand isolation — source 30e39aff
type: other
created_date: '2026-10-16 13:52'
updated_date: '2026-10-16 16:06'
---
Source commit: 30e39aff9f12c5f2059bce157d67de5e12319765 (task-365 slice 2). Recipient slice a843dbab0e510c3b1f738f251db3b0e59ed9dfec reviewed separately; completion-only f53eeb70ffb3bd116ac00a5335165706fa6fecf9 needs no tests.
Tests-branch batch commit: 638e6cf1766083cbc532168ee49efc8d7575204e. Previous branch tip: ef0e62e9e029cb89595e674713ec337a814d72c7, matching origin before publication.
Added file: backend/tests/test_expression_dictionary_safety.py.
Invariants (ADR-199 points 3, 5, 14): two concurrent first uses copy one starter dictionary; initialization neither commits nor rolls back unrelated caller work; another brand's entries cannot be listed, changed or deleted. Uses existing temp_brand/foreign_brand fixtures, admin context and independent PostgreSQL sessions. No production, accepted tasks, ADRs or config changed. No matching task-315 through task-323 bug; these are coverage additions for task-365.

Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-outcome-assets-fixed/newsletter-reference-implementation, exact source 30e39aff9f12c5f2059bce157d67de5e12319765 (earlier recipient test run pinned exactly to a843dbab0e510c3b1f738f251db3b0e59ed9dfec). Disposable PostgreSQL app_test_newsletter_reference_implementation_03c25d; TEST_DATABASE_URL unset, backend/.env absent, dotenv disabled; backend runs serialized and mock providers plus suite-wide real-vendor refusal guard retained. Shared checkout and dependency installations unchanged; frontend reuses node_modules via symlink.

Exact commands and results:
From backend at a843dba:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_recipient_personal_fields.py -q: 7 passed, exit 0.
From backend at 30e39af:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_expression_dictionary_safety.py tests/test_expressions.py tests/test_recipient_personal_fields.py -q: 46 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 2027 passed, 10 existing skips, exit 0, 82.77 seconds; log /private/tmp/regression-expressions-backend.log.
From frontend at 30e39af:
- node node_modules/vitest/vitest.mjs run: 313 passed, exit 0; log /private/tmp/regression-expressions-frontend.log.
- node node_modules/typescript/bin/tsc -b: exit 0.
From snapshot root:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_expression_dictionary_safety.py: exit 0.
Contract: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python exported main.app.openapi() after setting DATABASE_URL=tests.checkout_database.test_database_url(), to /private/tmp/regression-expressions-openapi.json (exit 0). From frontend: node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-expressions-openapi.json -o /private/tmp/regression-expressions-schema.d.ts; diff -u src/api/schema.d.ts /private/tmp/regression-expressions-schema.d.ts: exit 0, no difference. No tracked generated output written.

Discrimination: runtime-only pytest plugin monkeypatched sqlalchemy.orm.Query.with_for_update to return the query unchanged and ran pytest.main(['tests/test_expression_dictionary_safety.py::test_two_first_uses_copy_one_dictionary','-q'],plugins=[Probe()]). The strict regression failed (exit 1) with duplicate (brand_id, name) IntegrityError. No production file edited. The subsequent normal full suite above passed all three new cases. Parent comparison is not applicable: the dictionary did not exist before this source.

Known-bug failures: none. Test development corrections: the first file-write command used backend/tests relative to backend and failed before writing, followed by pytest exit 4/no tests; corrected to tests/. Initial transaction fixture relied on autoflush (disabled here), causing a test assertion and teardown error; corrected setup explicitly flushes unrelated content and rolls back in finally. Final targeted/full runs have no assertion or teardown failures. No skip/xfail or weakened invariant introduced. Default-sandbox ls-remote initially failed DNS; elevated read-only ls-remote succeeded and confirmed origin ef0e62e. No remaining infrastructure blocker. Existing Starlette/httpx and Vite configuration warnings remain.

Coverage sufficient for these two implemented slices. Migration 0051 upgrades of legacy databases are unverified (suite rebuilds from models); rendering, escaping, snapshot substitution and privacy behavior are later task-365 slices, not claimed implemented or covered here. No new product defect found in this bounded review.

Persistent tests branch retains its older production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and every earlier batch. Expression modules are absent on that base; passing intended-source validation above must not be read as collection or passing-suite validation on the tests branch. No production history merged. All earlier test batches have been integrated in source; only this new batch will await integration. Origin push: succeeded, exit 0; explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests advanced origin ef0e62e to 638e6cf1766083cbc532168ee49efc8d7575204e. Independent ls-remote verified the exact SHA. Commit parent and only changed path were checked, and tests worktree was clean. Integration pending for this new batch. This note is separate from the tests branch and must never be included in the batch commit.




## Integration verified 2026-10-16

Source 0e61c5aae3c5a9407a806218c4a73ec540e06fae integrates all three personalisation files from batches 638e6cf1766083cbc532168ee49efc8d7575204e, 526dec8dddce5721f87ace2fbc69db6d3c32602e and d29f10a602bbea9cd62d02090e9c1dee3515bbe8 unchanged. git diff d29f10a602bbea9cd62d02090e9c1dee3515bbe8 0e61c5aae3c5a9407a806218c4a73ec540e06fae -- backend/tests/test_expression_dictionary_safety.py backend/tests/test_expression_write_atomicity.py backend/tests/test_personalised_delivery_safety.py: empty, exit 0.

Independent exact-source snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-content-figures/newsletter-reference-implementation at 0e61c5a. Unique disposable PostgreSQL app_test_newsletter_reference_implementation_165cdf; TEST_DATABASE_URL unset and backend/.env absent, no .env read; dotenv disabled, mock providers and existing vendor refusal guard. From backend: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_expression_dictionary_safety.py tests/test_personalised_delivery_safety.py tests/test_expression_write_atomicity.py -q: 9 passed, exit 0. The earlier validation worktree's untracked copies remain preserved. This is targeted integration verification, not a fresh full-suite run at 0e61c5a. No personalisation batch remains pending integration. No new test commit/push was needed for this integration check.
