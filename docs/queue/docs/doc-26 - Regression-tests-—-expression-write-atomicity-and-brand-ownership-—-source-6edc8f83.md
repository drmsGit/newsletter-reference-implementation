---
id: doc-26
title: >-
  Regression tests — expression write atomicity and brand ownership — source
  6edc8f83
type: other
created_date: '2026-10-16 14:52'
updated_date: '2026-10-16 16:06'
---
Source commit: 6edc8f83d6d927abee67966fb450618975d9dee9 (task-365 slice 4). Tests-branch batch commit: d29f10a602bbea9cd62d02090e9c1dee3515bbe8; previous tip 526dec8dddce5721f87ace2fbc69db6d3c32602e, matching origin before this batch.
Added file: backend/tests/test_expression_write_atomicity.py.
Invariants (ADR-199 point 9 and changed-values contract, ADR-180 version tokens): a refused envelope write rolls back its rename and version as well as subject/preheader; a dictionary entry owned only by another brand is rejected in module, content and override writes, preserving prior values, versions and the active override. Four strict API cases using existing signed_in and expression-check fixtures and independent sessions for persisted-state checks. No production, configuration, ADRs or accepted tasks changed. Task-322 supplies the existing atomic-envelope context; no reopened task-315..323 defect is claimed. These are additional task-365 tests.

Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-outcome-assets-fixed/newsletter-reference-implementation pinned to exact source above. Disposable PostgreSQL app_test_newsletter_reference_implementation_03c25d; no TEST_DATABASE_URL override, backend/.env absent, dotenv disabled, mock providers and suite-wide real-vendor refusal guard. Backend runs serialized. Prior batches' untracked test copies preserved and included in full backend suite. No shared checkout edits except this authorized primary handoff note; no dependency installations changed.

Commands from snapshot backend:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_expression_checks.py -q: 17 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_expression_write_atomicity.py tests/test_expression_checks.py -q: 21 passed, exit 0.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache tests/test_expression_write_atomicity.py: exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 2062 passed, 10 existing skips, exit 0, 80.17 seconds; /private/tmp/regression-expression-writes-backend.log.
From snapshot frontend:
- node node_modules/vitest/vitest.mjs run: 317 passed, exit 0; /private/tmp/regression-expression-writes-frontend.log.
- node node_modules/typescript/bin/tsc -b: exit 0.
Contract: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python exported main.app.openapi() with DATABASE_URL=tests.checkout_database.test_database_url() to /private/tmp/regression-expression-writes-openapi.json, exit 0. Frontend node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-expression-writes-openapi.json -o /private/tmp/regression-expression-writes-schema.d.ts; diff -u src/api/schema.d.ts /private/tmp/regression-expression-writes-schema.d.ts: exit 0, no schema difference. No tracked generated output changed.

Discrimination: runtime-only pytest plugin replaced app.campaigns.service.set_envelope_fields with a wrapper that commits before the original check, then ran pytest.main(['tests/test_expression_write_atomicity.py::test_a_refused_envelope_also_rolls_back_the_rename_and_version','-q'],plugins=[Probe()]). The new test failed, exit 1: the API still returned 422, but the rename/version persisted. Normal full suite afterwards passed. No production file edited. Parent behavior lacks these save checks; no parent comparison claimed.

Known-bug failures in this batch: none. Existing task-385 was filed by documentation commit b99bda3c5910d074546a9ded187275f70d90710f and a subsequent client fix 1cf951f3dd7e34a4b288fa3bc34e42f3b5c08eea arrived during validation; that fix is a separate review. Documentation commit 994cb18a456db926795d5418711b98dcf7f78303 adds ADR/privacy explanations; documentation-only commits reviewed separately need no tests.
Test development corrections: the first module fixture used a catalogue-owned field as module data and was refused by an earlier schema guard, so it was corrected to a writable CTA label; dictionary rejection and all persistence assertions remain strict. A database helper invocation from the snapshot root failed import before any tests and was repeated successfully from backend. An initial lint invocation from the primary checkout named the absent file and only warned; the actual isolated-file Ruff command above succeeded. No remaining infrastructure failure or teardown error. Existing Starlette/httpx and Vite warnings remain. No skip/xfail/weakening introduced.

Coverage sufficient for the bounded save-check/picker changes reviewed, with existing client caret insertion and rejection-location tests. Real browser interactions, legacy migration upgrades and privacy erasure remain unverified; erasure is explicitly unimplemented, as the new documentation says.
Persistent tests branch keeps production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and all earlier batches including 638e6cf1766083cbc532168ee49efc8d7575204e and 526dec8dddce5721f87ace2fbc69db6d3c32602e. New modules/fixtures are absent from that older base; these passing results validate the exact intended source, not collection or a full passing suite on the tests branch. No production merged. All three new batches await integration. Origin push: succeeded, exit 0; explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests advanced origin from 526dec8 to d29f10a602bbea9cd62d02090e9c1dee3515bbe8. Independent ls-remote verified the exact SHA. Before commit, branch identity, previous tip, staged path, exact diff and allowed-path restriction were checked; after commit, parent, single allowed changed file and clean tests worktree were verified. Integration pending. This primary note is separate from the test commit.



Subsequent independent client review: exact 1cf951f3dd7e34a4b288fa3bc34e42f3b5c08eea (task-385) was tested in the same isolated worktree after this batch had been validated/published. From snapshot root: node frontend/node_modules/vitest/vitest.mjs run --root frontend: all 319 passed, exit 0 (/private/tmp/regression-trim-frontend.log). From frontend: node node_modules/typescript/bin/tsc -b: exit 0. Existing trimming-store and real-overwrite cases are sufficient for this small fix, so no extra test batch. Backend executable code/tests unchanged since 6edc8f8; backend full suite was not rerun at 1cf951f. Completion/erasure-question documentation e9c020f830ad5164ad17fe7587edad1ed26d1bab reviewed separately, no tests needed. These follow-up checks do not change this batch's intended validation source.



## Integration verified 2026-10-16

Source 0e61c5aae3c5a9407a806218c4a73ec540e06fae integrates all three personalisation files from batches 638e6cf1766083cbc532168ee49efc8d7575204e, 526dec8dddce5721f87ace2fbc69db6d3c32602e and d29f10a602bbea9cd62d02090e9c1dee3515bbe8 unchanged. git diff d29f10a602bbea9cd62d02090e9c1dee3515bbe8 0e61c5aae3c5a9407a806218c4a73ec540e06fae -- backend/tests/test_expression_dictionary_safety.py backend/tests/test_expression_write_atomicity.py backend/tests/test_personalised_delivery_safety.py: empty, exit 0.

Independent exact-source snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-content-figures/newsletter-reference-implementation at 0e61c5a. Unique disposable PostgreSQL app_test_newsletter_reference_implementation_165cdf; TEST_DATABASE_URL unset and backend/.env absent, no .env read; dotenv disabled, mock providers and existing vendor refusal guard. From backend: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_expression_dictionary_safety.py tests/test_personalised_delivery_safety.py tests/test_expression_write_atomicity.py -q: 9 passed, exit 0. The earlier validation worktree's untracked copies remain preserved. This is targeted integration verification, not a fresh full-suite run at 0e61c5a. No personalisation batch remains pending integration. No new test commit/push was needed for this integration check.
