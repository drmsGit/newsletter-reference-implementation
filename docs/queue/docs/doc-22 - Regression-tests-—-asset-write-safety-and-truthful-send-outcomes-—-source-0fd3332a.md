---
id: doc-22
title: >-
  Regression tests — asset write safety and truthful send outcomes — source
  0fd3332a
type: other
created_date: '2026-10-15 20:02'
updated_date: '2026-10-16 13:00'
---
Source covered: 0fd3332a14e0a4c7b2897cc3f6abd431183722ed, including asset backend source 3849d18b126f66314ecb81d65fd512db5c4f6238 and the send screen introduced in 6a8c8caf008b3d3cb3ff011b5f86b6db36d0611b, updated in 206ca18554cb2958b764ebbaccf69aa0e6293216.
Tests-branch batch commit: 7035896973382929db3c28eb6610ff924a92a5ac; previous tip d7051b827e5b048dfdfc3726682f123228314181.
Added files:
- backend/tests/test_asset_write_safety.py: concurrent replacement of one address; a failed disk write preserves prior bytes/metadata; cross-brand replace/alt/hide all refused.
- frontend/src/screens/SendVariant.outcome.test.tsx: failed, partial_failed and no_recipients outcomes must not be labelled Sent.

ADRs: ADR-197 points 2/10/11 for replacement and brand isolation; ADR-183 for send flow. Task-323 (original review DRAFT-6/doc-1) supplies the truthful-outcome contract. Completed task-323 repaired the API; the new React screen reintroduces misleading wording. The new asset concurrency defect belongs to task-112's implementation and has no matching promoted task among task-315 through task-323; do not relabel it as one of those. No accepted task or production file changed.

Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-send-assets/newsletter-reference-implementation, detached at exact source above. Disposable PostgreSQL app_test_newsletter_reference_implementation_e7ad62, no override or .env read. Backend suites serialized; real email/AI vendor guard verified and mock providers used. Asset files use per-test temporary storage.

Exact commands (from snapshot backend unless stated):
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_asset_write_safety.py tests/test_assets.py -q: 34 passed, 1 failed, exit 1. Failure: test_overlapping_replacements_of_one_address_both_finish; second rename raises FileNotFoundError because both put calls share <token>.part. Both writes reach the rename boundary under controlled overlap; the test also permits an implementation that serializes replacements.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 1954 passed, 10 existing skips, 1 failed, exit 1 (86.24s). Only the new concurrent replacement case failed.
From snapshot frontend:
- node node_modules/vitest/vitest.mjs run src/screens/SendVariant.outcome.test.tsx src/components/ImageField.test.tsx src/components/ImageField.upload.test.tsx: 7 passed, 3 failed, exit 1. All three new task-323 cases receive Sent: failed., Sent: partial failed., or Sent: no recipients.
- node node_modules/vitest/vitest.mjs run: 293 passed, 3 failed, exit 1, only those new task-323 cases.
- node node_modules/typescript/bin/tsc -b: exit 0 (independently checked).
- node node_modules/eslint/bin/eslint.js src/screens/SendVariant.outcome.test.tsx: exit 0.
From snapshot root:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_asset_write_safety.py: exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python exported main.app.openapi() after DATABASE_URL=tests.checkout_database.test_database_url() to /private/tmp/regression-send-assets-openapi.json; from frontend node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-send-assets-openapi.json -o /private/tmp/regression-send-assets-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/regression-send-assets-schema.d.ts: exit 0, no schema difference.

Known-bug failures are strict and preserved, no skip/xfail/weakening. No passing-suite or coverage-sufficiency claim. Two asset error/isolation cases pass; initial test fixture cleanup ordering was corrected and the rerun has no teardown error. No infrastructure failures remain. Legacy migration 0050 upgrades unverified; suites rebuild from models. Actual multipart serialization in the client remains unverified because the existing upload test replaces its hook; backend multipart route behavior is covered by existing asset tests. Pre-asset comparison is not applicable (asset module absent); current strict cases reproduce the defects on intended committed source.

Persistent tests branch retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and earlier batches. New source modules/fixtures are absent on that base: these results validate the intended source, not the older tests-branch production base. No production merged into tests branch.
Origin push: succeeded, exit 0, explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests; independently verified origin SHA 7035896973382929db3c28eb6610ff924a92a5ac. Commit parent is the prior tip and exactly the two allowed test files changed; worktree clean. Integration pending for this batch. Earlier 6d376949 and d7051b827 were integrated unchanged by e0a30ed0bf11e533d82f671a0ceecd56e09b62f7; 3 exact-source regression cases passed there.
This note is separate from the test commit.



## Integration verified 2026-10-16

Both files from batch 7035896973382929db3c28eb6610ff924a92a5ac are now integrated into source history. Task-382: b2f085c0a21f911daa0afe2f70d0058b844790b4 adapted SendVariant.outcome.test.tsx to the truthful sentences while retaining strict failure assertions, adding successful and reopened-page cases. Task-383: 48377038b3a31568cae2998396305d2045e8d4b0 preserves all original asset test cases unchanged and adds rename-failure cleanup and real PostgreSQL row-lock contention checks. These defects now have their own promoted tasks, task-382 and task-383; task-323 remains the original API contract context. Completion-only documentation commits 6b7a1e77ea2da88b68e17b304ec47ae16d8a08c5 and 91c6eee5ec722c621fcd859377893112fae8b968 were reviewed separately; no tests required for those commits.

Independent validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-outcome-assets-fixed/newsletter-reference-implementation. Tested first at exact b2f085c0a21f911daa0afe2f70d0058b844790b4, then advanced only this isolated snapshot to exact 48377038b3a31568cae2998396305d2045e8d4b0. No shared checkout or earlier test additions modified. Disposable database app_test_newsletter_reference_implementation_03c25d; no TEST_DATABASE_URL override, backend/.env absent, dotenv disabled, mock providers and the existing real-vendor refusal guard. Backend runs serialized.

At b2f085c, from frontend:
- node node_modules/vitest/vitest.mjs run src/screens/SendVariant.outcome.test.tsx src/screens/SendVariant.test.tsx: 19 passed, exit 0.
- node node_modules/vitest/vitest.mjs run: 308 passed, no failures.
- node node_modules/typescript/bin/tsc -b: exit 0. The full-suite/typecheck command completed exit 0.
At 4837703, from backend:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_asset_write_safety.py tests/test_assets.py -q: 39 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 1980 passed, 10 existing skips, exit 0, 77.21 seconds.
From snapshot root at 4837703:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_asset_write_safety.py backend/app/assets/store.py backend/app/assets/service.py: exit 0.
- node frontend/node_modules/typescript/bin/tsc -b frontend: exit 0.
The frontend tree is identical between the two tested commits. No infrastructure failures; the existing Starlette/httpx deprecation warning remains. Real email client checks, legacy migration upgrades and process-crash file cleanup remain unverified. Coverage is sufficient for these two bounded fixes; no additional tests or new test-batch commit/push was needed. The persistent tests branch and its previous successful publication are preserved. Column batch ef0e62e9e029cb89595e674713ec337a814d72c7 remains awaiting integration under task-384.



Subsequent integration update 2026-10-16: Column batch ef0e62e9e029cb89595e674713ec337a814d72c7 landed unchanged in 5c1a52a86e4802b9246bb4af90699bbcd4632c18 and its exact-source targeted regression passed (doc-23). No test batches remain pending integration.
