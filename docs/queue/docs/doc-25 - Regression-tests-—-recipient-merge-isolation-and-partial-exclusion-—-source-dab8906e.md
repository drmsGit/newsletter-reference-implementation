---
id: doc-25
title: >-
  Regression tests — recipient merge isolation and partial exclusion — source
  dab8906e
type: other
created_date: '2026-10-16 13:57'
updated_date: '2026-10-16 16:06'
---
Source commit: dab8906ee8c6f3243e164a18c4ca2bff0e23c54b (task-365 slice 3; ADR-199 points 10–13 and ADR-183). Tests-branch batch commit: 526dec8dddce5721f87ace2fbc69db6d3c32602e; previous tip 638e6cf1766083cbc532168ee49efc8d7575204e, matching origin.
Added file: backend/tests/test_personalised_delivery_safety.py.
Invariants: one send records and reconstructs each recipient's own resolved values without leaking another recipient's names; a missing-language slot pick excludes only that recipient, leaves no sent artifact record/hash for them, and still sends and reconstructs the healthy recipient. Uses existing test_personalised_rendering db/world/setup fixtures, mock delivery capture, frozen content versions and actual delivery loop. No production, config, ADR or accepted-task changes. No corresponding open task-315 through task-323 defect; coverage additions for task-365.

Validation snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-outcome-assets-fixed/newsletter-reference-implementation, detached at exact dab8906ee8c6f3243e164a18c4ca2bff0e23c54b. Disposable PostgreSQL app_test_newsletter_reference_implementation_03c25d, no TEST_DATABASE_URL override, backend/.env absent; dotenv disabled and mock providers plus suite-wide real-vendor refusal guard retained. Backend runs serialized. Prior new dictionary safety tests preserved in this snapshot and included in the full run. Shared checkout and installations untouched.

Exact commands from backend:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_personalised_rendering.py tests/test_column_slot_delivery.py tests/test_frame.py -q: 31 passed, exit 0, before additional tests.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_personalised_delivery_safety.py tests/test_personalised_rendering.py -q: 14 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 2041 passed, 10 existing skips, exit 0, 90.83 seconds; /private/tmp/regression-personalised-backend.log.
From snapshot root:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_personalised_delivery_safety.py: exit 0.
Contract: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python exported main.app.openapi() with DATABASE_URL=tests.checkout_database.test_database_url() to /private/tmp/regression-personal-openapi.json, exit 0. From frontend: node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-personal-openapi.json -o /private/tmp/regression-personal-schema.d.ts; diff -u src/api/schema.d.ts /private/tmp/regression-personal-schema.d.ts: exit 0, no schema difference. No tracked generated file changed.
The frontend tree is unchanged from 30e39aff9f12c5f2059bce157d67de5e12319765, whose full frontend suite passed all 313 cases and tsc -b exited 0 (doc-24). Not rerun at dab8906; do not describe it as a new exact-source client run.

Discrimination: runtime-only pytest plugin cached the first recipient's app.expressions.substitute.recipient_fields result for subsequent recipients and invoked pytest.main(['tests/test_personalised_delivery_safety.py::test_one_send_keeps_each_recipients_values_separate','-q'],plugins=[Probe()]). The new test failed, exit 1: both mocked messages used Anna's values rather than Ben's. No production file changed. Normal targeted run and subsequent full suite above passed. Rendering/substitution did not exist at the parent; no parent pass/fail comparison claimed.

Known-bug failures: none. Coverage sufficient for the bounded rendering changes reviewed, with per-recipient isolation and partial exclusions added to existing escaping, old-frame compatibility and frozen reconstruction checks. No assertion weakening, skip or xfail. Unverified: real mail-client rendering, legacy migration upgrades, and later task-365 save-validation/picker/erasure work. Existing Starlette/httpx deprecation warning remains. No infrastructure blocker. An empty note was accidentally created via Backlog in the validation snapshot (doc-10 there); it is untracked, has no test content, and is excluded from the tests branch. This primary-repository doc-25 is the actual handoff note.

Persistent tests branch retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a, all older batches and new dictionary batch 638e6cf1766083cbc532168ee49efc8d7575204e. New expressions modules/fixtures are absent at that old base; validation above is against intended source, not collection or full-suite validation on the tests branch. No production history merged. Both this batch and 638e6cf await integration. Origin push: succeeded, exit 0, explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. Origin advanced 638e6cf to 526dec8dddce5721f87ace2fbc69db6d3c32602e; independently verified by ls-remote. Parent, clean tests worktree and single allowed changed file were checked. Integration pending. This note must remain outside the tests-branch commit.




## Integration verified 2026-10-16

Source 0e61c5aae3c5a9407a806218c4a73ec540e06fae integrates all three personalisation files from batches 638e6cf1766083cbc532168ee49efc8d7575204e, 526dec8dddce5721f87ace2fbc69db6d3c32602e and d29f10a602bbea9cd62d02090e9c1dee3515bbe8 unchanged. git diff d29f10a602bbea9cd62d02090e9c1dee3515bbe8 0e61c5aae3c5a9407a806218c4a73ec540e06fae -- backend/tests/test_expression_dictionary_safety.py backend/tests/test_expression_write_atomicity.py backend/tests/test_personalised_delivery_safety.py: empty, exit 0.

Independent exact-source snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-content-figures/newsletter-reference-implementation at 0e61c5a. Unique disposable PostgreSQL app_test_newsletter_reference_implementation_165cdf; TEST_DATABASE_URL unset and backend/.env absent, no .env read; dotenv disabled, mock providers and existing vendor refusal guard. From backend: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_expression_dictionary_safety.py tests/test_personalised_delivery_safety.py tests/test_expression_write_atomicity.py -q: 9 passed, exit 0. The earlier validation worktree's untracked copies remain preserved. This is targeted integration verification, not a fresh full-suite run at 0e61c5a. No personalisation batch remains pending integration. No new test commit/push was needed for this integration check.
