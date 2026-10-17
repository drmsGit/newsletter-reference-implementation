---
id: doc-18
title: Regression tests — stored session safety — source 9f36608e
type: other
created_date: '2026-10-11 12:57'
updated_date: '2026-10-11 13:55'
---
Source covered: 9f36608e55f48101711808178a9534a52d98c121, task-342, ADR-151 addenda of 2026-10-09 and 2026-10-11.
Batch commit: 5caf6a591b3c92e7836f320e9a031070e845cba3. Origin push succeeded, exit 0, explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests refspec; git ls-remote confirmed the same full SHA. Allowed-path restriction checked before commit and push; prior batches preserved.
Added file: backend/tests/test_session_lengths_stored_safety.py.
Four behavioral cases: stored lengths above bounds, below bounds, malformed strings and idle longer than lifetime yield safe settings; a freshly active session remains valid one second before the resulting absolute limit and is refused exactly at it. Existing tests covered setting validation and changed lengths but not stored-value corruption. No remaining defect exposed by these cases. Parent lacks the new settings API/helper, so a parent replay of this file would be a collection failure rather than meaningful mutation evidence; no production code altered.

Exact snapshot worktree: /Users/diedeslembrouck/.codex/worktrees/regression-session-lengths/newsletter-reference-implementation, detached at source above. Disposable DB app_test_newsletter_reference_implementation_c357c2; no TEST_DATABASE_URL override or backend/.env, development DB refused by harness, mock-provider guards active, no real email. Existing frontend node_modules reused by symlink without installation changes.

Validation:
- At 5e39bfd65a2096f8f95ae385b18353e6e4c8908f: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q backend/tests/test_unattended_empty_due.py backend/tests/test_unattended_ceiling.py --tb=short: 14 passed, exit 0. e380c645's test integrated byte-for-byte with fix; doc-17 updated and read back.
- At exact source 9f36608, root cwd: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q backend/tests/test_session_lengths_stored_safety.py backend/tests/test_session_lengths.py backend/tests/test_settings_api.py --tb=short: 51 passed, exit 0.
- Isolated backend cwd: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests --tb=short: 1828 passed, 10 existing skips, exit 0.
- Isolated backend cwd: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache tests/test_session_lengths_stored_safety.py: exit 0.
- Isolated frontend cwd: node node_modules/vitest/vitest.mjs run: 268 passed, 32 files, exit 0; node node_modules/typescript/bin/tsc -b: exit 0.
- Contract: app.openapi() exported to /private/tmp/session-lengths-openapi.json with DATABASE_URL from tests.checkout_database.test_database_url(); node node_modules/openapi-typescript/bin/cli.js /private/tmp/session-lengths-openapi.json -o /private/tmp/session-lengths-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/session-lengths-schema.d.ts: exit 0.
Infrastructure failures: none. Full suite is source plus this new file; it does NOT include the still-unintegrated c0cd3bf transactional-rule/session-read batch. The prior two strict transactional-rule failures remain pending integration/fix; their status must not be hidden by this passing suite. No global coverage-sufficiency claim; reviewed session-settings gaps covered.

Persistent tests branch: /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation. Previous tip e380c6452d064682e473b74e26c6e72413f0b835 preserved. Production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a; no production history merged. Intended-source validation above is not validation against that older base, which lacks test_session_lengths and its production settings. Integration pending.


Integration verified 2026-10-11 against exact source 80e9e1e5b955632a1e9be17ccef59048b28c028a. Isolated managed worktree /Users/diedeslembrouck/.codex/worktrees/regression-purpose-integrated/newsletter-reference-implementation; separate disposable DB app_test_newsletter_reference_implementation_2435c5, no .env read, no real email. Published test files from c0cd3bf and 5caf6a5 match byte-for-byte. Transactional include/exclude regressions now pass, along with profile-less session-read and stored session-safety tests. These batches are integrated with the fix; the earlier transactional defects are resolved in this source.

Commands in isolated backend:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_transactional_rule_purpose.py tests/test_brand_session_read.py tests/test_session_lengths_stored_safety.py tests/test_transactional.py tests/test_audience_arithmetic.py tests/test_brand_boundary.py --tb=short: 65 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests --tb=short: 1831 passed, 10 existing skips, exit 0.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache app/audience/service.py tests/test_audience_arithmetic.py tests/test_transactional_rule_purpose.py tests/test_brand_session_read.py tests/test_session_lengths_stored_safety.py: exit 0.
- git diff --check: exit 0.
Initial targeted command named nonexistent test_push_rule_channel.py and exited 4 without running tests; corrected to existing paths above. No remaining infrastructure blocker. No frontend or API contract changes in this source commit; relevant full backend suite is green. No new coverage gap identified in the reviewed fix; no empty test commit created. Tests branch remains unchanged at 5caf6a591b3c92e7836f320e9a031070e845cba3 and origin confirmed the same SHA.
