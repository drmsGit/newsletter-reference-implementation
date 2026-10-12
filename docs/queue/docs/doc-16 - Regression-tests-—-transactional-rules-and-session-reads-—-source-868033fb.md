---
id: doc-16
title: Regression tests — transactional rules and session reads — source 868033fb
type: other
created_date: '2026-10-11 12:02'
updated_date: '2026-10-11 13:55'
---
Source covered: 868033fb033d6ccc35283ebefa29f2bdd64d295f. Transactional behavior introduced by 68c7f1fe2f474ea4421c143299ecc8f00af92825; session-logo read introduced by a0f7cda74f150068f5223255d19e97edaf1376e8 and corrected by 868033fb.

Batch commit: c0cd3bf75f3bbadf041203894f300ef91f504e1e. Origin push succeeded (exit 0), explicit refs/heads/codex/regression-tests refspec; git ls-remote confirmed the same full SHA. Both committed paths passed the allowed-path restriction; earlier batches remain preserved. Integration pending.

Files:
- backend/tests/test_transactional_rule_purpose.py
- backend/tests/test_brand_session_read.py

Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-transactional/newsletter-reference-implementation, detached at exact source 868033fb. Disposable database app_test_newsletter_reference_implementation_a2c648, distinct from development. No .env read, real email, or shared dependency installation changes.

Known defects associated with task-355, not tasks 315–323: transactional include rule matching still requires marketing consent, omitting eligible recipients; transactional exclude matching misses a non-opted-in pinned recipient, allowing delivery despite an explicit exclusion. ADR-195 governs transactional purpose; ADR-176 governs negative rules winning over pins. Both assertions stay strict, with no skip/xfail. Existing pin-only transactional coverage missed these rule paths. The session-read invariant (task-356; ADR-194 brand context) fails on a0f7cda and passes at 868033fb: reading a profile-less brand's session must not create a default profile.

Commands run from isolated backend using PYTHON_DOTENV_DISABLED=1 and /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python:
- -m pytest -q tests/test_transactional.py tests/test_brand_profile_api.py tests/test_permission_split.py: 51 passed at 68c7f1f, exit 0.
- -m pytest -q tests/test_transactional_rule_purpose.py --tb=short: 2 failed at 68c7f1f, exit 1 (the two defects above; initial fixture scoping/cleanup errors were corrected before final verification).
- -m pytest -q tests/test_profile_link_attribution_boundary.py tests/test_profile_theme.py: 21 passed at e486157, exit 0; earlier batch c6af95c's test is integrated byte-for-byte with the fix.
- -m pytest -q tests/test_brand_logo.py: 3 passed at a0f7cda, exit 0.
- -m pytest -q tests/test_brand_session_read.py --tb=short: 1 failed at a0f7cda, exit 1; count 1 instead of 0 proves the regression.
- -m pytest -q tests/test_transactional_rule_purpose.py tests/test_brand_session_read.py tests/test_transactional.py tests/test_brand_logo.py --tb=short: 20 passed, 2 failed at 868033fb, exit 1; only the transactional rule defects fail.
- -m pytest -q tests --tb=short: 1794 passed, 10 existing skips, 2 failed, exit 1; only the same two strict new tests fail.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check tests/test_transactional_rule_purpose.py tests/test_brand_session_read.py: exit 0.

Frontend commands at a0f7cda: node node_modules/vitest/vitest.mjs run src/shell/Shell.test.tsx: 2 passed, exit 0.
Frontend commands at 868033fb: node node_modules/vitest/vitest.mjs run: 267 passed across 32 files, exit 0; node node_modules/typescript/bin/tsc -b: exit 0.
Contract at 868033fb: app.openapi() exported to /private/tmp/transactional-openapi.json with DATABASE_URL set via tests.checkout_database.test_database_url(); node node_modules/openapi-typescript/bin/cli.js /private/tmp/transactional-openapi.json -o /private/tmp/transactional-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/transactional-schema.d.ts: exit 0.
git diff --check: exit 0.

Infrastructure failures: none in final validation. Backend suite is not green and coverage sufficiency is not claimed.

Persistent branch worktree: /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation. Previous tip c6af95c9b64fb028244585f383de5ed197e3fb02 preserved; production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a. No production history merged. These tests import source fixtures/modules absent from the older base; source validation above must not be interpreted as passing validation on the tests branch's older production base. Integration requires current production source; strict failing tests should land with the transactional rule fix.


Integration verified 2026-10-11 against exact source 80e9e1e5b955632a1e9be17ccef59048b28c028a. Isolated managed worktree /Users/diedeslembrouck/.codex/worktrees/regression-purpose-integrated/newsletter-reference-implementation; separate disposable DB app_test_newsletter_reference_implementation_2435c5, no .env read, no real email. Published test files from c0cd3bf and 5caf6a5 match byte-for-byte. Transactional include/exclude regressions now pass, along with profile-less session-read and stored session-safety tests. These batches are integrated with the fix; the earlier transactional defects are resolved in this source.

Commands in isolated backend:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_transactional_rule_purpose.py tests/test_brand_session_read.py tests/test_session_lengths_stored_safety.py tests/test_transactional.py tests/test_audience_arithmetic.py tests/test_brand_boundary.py --tb=short: 65 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests --tb=short: 1831 passed, 10 existing skips, exit 0.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache app/audience/service.py tests/test_audience_arithmetic.py tests/test_transactional_rule_purpose.py tests/test_brand_session_read.py tests/test_session_lengths_stored_safety.py: exit 0.
- git diff --check: exit 0.
Initial targeted command named nonexistent test_push_rule_channel.py and exited 4 without running tests; corrected to existing paths above. No remaining infrastructure blocker. No frontend or API contract changes in this source commit; relevant full backend suite is green. No new coverage gap identified in the reviewed fix; no empty test commit created. Tests branch remains unchanged at 5caf6a591b3c92e7836f320e9a031070e845cba3 and origin confirmed the same SHA.
