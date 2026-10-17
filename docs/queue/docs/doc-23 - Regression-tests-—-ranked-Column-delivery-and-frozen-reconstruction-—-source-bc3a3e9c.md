---
id: doc-23
title: >-
  Regression tests — ranked Column delivery and frozen reconstruction — source
  bc3a3e9c
type: other
created_date: '2026-10-16 02:35'
updated_date: '2026-10-16 13:00'
---
Source commit: bc3a3e9cc86ff9e776e60c0fb5cd8f5d248385e4 (task-371; ADR-198, ADR-084, ADR-183).
Tests-branch batch commit: ef0e62e9e029cb89595e674713ec337a814d72c7; previous tip 7035896973382929db3c28eb6610ff924a92a5ac.
Added file: backend/tests/test_column_slot_delivery.py.
Invariant: three ranked picks in one Column slot are sent as one pair and a lone Column; each link credits its own record, and the sent body/modules/hash reconstruct unchanged after today's hidden fields and ranked-set length change. Uses existing mock-send and catalogue fixtures.

Validation snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-send-assets/newsletter-reference-implementation pinned to the exact source above. Confirmed unique disposable PostgreSQL app_test_newsletter_reference_implementation_e7ad62; no TEST_DATABASE_URL override or backend/.env; suite-wide real-vendor guard and mock provider, backend suites serialized. Shared checkout and dependency installations untouched.

Exact commands from snapshot backend:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_block_set.py tests/test_several_picks.py tests/test_frame.py tests/test_assets.py -q: 87 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_column_slot_delivery.py tests/test_block_set.py -q: 19 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 1975 passed, 10 existing skips, 4 failed, exit 1 (149.75s). One failure is the preserved asset-replacement race. Three unchanged time-sensitive checks failed: test_accepts_a_correctly_signed_body; test_the_route_refuses_a_well_signed_event_while_the_secret_is_unset; TestASendNamesWhoFiredIt.test_a_scheduled_send_fired_by_the_scheduler. The webhook log reports a 1019-second stale timestamp.
From snapshot frontend:
- node node_modules/vitest/vitest.mjs run: 300 passed, 3 failed, exit 1. The three strict cases from earlier batch 703589697 in SendVariant.outcome.test.tsx still expose task-323's client outcome regression (failed / partial_failed / no_recipients all prefixed Sent).
- node node_modules/typescript/bin/tsc -b: exit 0.
- node scripts/build-modules.mjs --check: exit 0, all 9 compiled files current, check mode only (no generated output changed).
From snapshot root:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_column_slot_delivery.py: exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python exported main.app.openapi() after setting DATABASE_URL=tests.checkout_database.test_database_url() to /private/tmp/regression-columns-openapi.json; from frontend node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-columns-openapi.json -o /private/tmp/regression-columns-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/regression-columns-schema.d.ts: exit 0, no differences.

Pre-change comparison: Column did not exist on the parent; no passing/failing parent validation claimed. Runtime-only fault probe via Python pytest.main(['tests/test_column_slot_delivery.py','-q'], plugins=[Probe()]), autouse monkeypatch setting app.rendering.service.module_part=module_html: 1 failed, exit 1, correctly detected 3 rows instead of 2. No production file changed. Then the unchanged normal command PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_column_slot_delivery.py -q passed (1 passed, exit 0).
Known open bugs from earlier batch are preserved strictly: concurrent asset replacements share a temporary filename (new asset defect associated with task-112, no matching task-315..323); client unsuccessful outcomes labelled Sent (task-323 contract regression). No production fixes, weakening, skip or xfail. No passing-suite or coverage-sufficiency claim.
Infrastructure: automatic approval review timed out before starting the first full backend request and MJML check. The backend command was retried once; MJML read-only check succeeded without elevation. Final verification outcomes below distinguish any remaining limitations. Legacy database migration upgrades and real email-client layout unverified.

Persistent tests branch remains based on production 28aa4e88f4846768a18fd81b66949f959cd3b38a, retaining all earlier batches. This file relies on newer source test fixtures unavailable at that old base; intended-source validation above is not validation against the tests branch's older production. No production merged into the tests branch.
Origin push: succeeded (exit 0), explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests, independently verified origin equals ef0e62e9e029cb89595e674713ec337a814d72c7. Commit parent is 7035896973382929db3c28eb6610ff924a92a5ac, its only changed path is backend/tests/test_column_slot_delivery.py, and tests worktree is clean. Integration pending. This pre-stage note is separate and must not be included in the test commit.

Follow-up to time-sensitive full-run failures: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_provider_webhook_signature.py tests/test_send_consent_audit.py -q: all 18 passed, exit 0, no source edits. Read-only application-versus-disposable-database clock comparison afterwards was 0.0 seconds. These are transient time-sensitive verification failures; no new production defect is claimed from them, and the original full run is still reported non-green. Approval timeouts were recovered; no remaining permission blocker. Real mail-client layout and migration upgrades remain unverified.



## Integration verified 2026-10-16

Integrated unchanged in 5c1a52a86e4802b9246bb4af90699bbcd4632c18 (task-384). git diff ef0e62e9e029cb89595e674713ec337a814d72c7 5c1a52a86e4802b9246bb4af90699bbcd4632c18 -- backend/tests/test_column_slot_delivery.py is empty, exit 0.

Independent exact-source snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-outcome-assets-fixed/newsletter-reference-implementation, detached at 5c1a52a86e4802b9246bb4af90699bbcd4632c18. Disposable PostgreSQL app_test_newsletter_reference_implementation_03c25d, no environment override or .env reads, dotenv disabled and mock vendor guards retained. From backend, PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_column_slot_delivery.py -q: 1 passed, exit 0. Initial invocation from the snapshot root used the wrong relative test path: exit 4, no tests ran; corrected backend invocation above passed. This was a command-path error, not a product failure.

The relevant full backend suite was independently run just before integration at exact production fix 48377038b3a31568cae2998396305d2045e8d4b0: 1980 passed, 10 existing skips, exit 0 (doc-22). Source changes since that snapshot are completion documentation and this unchanged test only. The entire suite was not rerun at 5c1a52a; exact-source verification here is the targeted regression. No new tests, production changes, test-batch commit or push needed; existing publication and all earlier test batches preserved. Both earlier strict known-bug failures were fixed/integrated under task-382 and task-383, independently verified in doc-22. No test batch remains awaiting integration after this commit.
