---
id: doc-36
title: Regression tests — preserve rich-text link targets — source 57e8151
type: other
created_date: '2026-10-17 20:04'
updated_date: '2026-10-17 20:08'
---
Source covered: 57e815106e9e2285f75e03a8d2a7b9f8e2486013, task-392 item 6 (rich-text italics and bullets).
Tests-branch batch: c4caca9a9741fe248300c8cc7b7b5ec3cb3518cf; parent 27148b5d844c59c444477e9120fd39f6350e0e72. Only backend/tests/test_rich_text_link_targets.py added, 27 lines, 2 parametrized cases. Earlier batches preserved. No production/config/docs files included in batch, no normal hook bypass. Branch identity, staged path and exact diff against previous tip checked; explicit git add of this single path.

Defect: formatting applies italic substitution after constructing anchors. [Search](https://example.test/search?q=*walking*&page=2) gets href containing <em>walking</em> instead of literal *walking*. HTMLParser checks actual href for inline and bullet-list links, decoding HTML ampersands. Both assertions remain strict, with no skips/xfails. Related to task-392 item 6; not task-315 through task-323. ADR-199 governs formatting boundaries; no ADR explicitly describes asterisk URL syntax. Production is unchanged. Tests await integration with the fix.

Source validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-send-outcome/newsletter-reference-implementation, pinned to source for source runs; now detached at d42d2df2822089448d7c0d24c3eda26ed4b2278e for the later review. New test copy is preserved there. Branch worktree: /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation. Tests branch retains older production base 28aa4e88f4846768a18fd81b66949f959cd3b38a; source results do not claim validation against that older base. No production merge. Committed file is byte-identical to validation copy.

Isolation: TEST_DATABASE_URL verified unset; checkout-derived app_test_newsletter_reference_implementation_32f1fd; every backend command uses PYTHON_DOTENV_DISABLED=1, harness-owned temporary asset directory, mock providers and suite real-vendor-network refusal. Backend suites serialized. No .env read, real mail or development database touched.

Commands/results (backend cwd, using /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python):
- At exact source: PYTHON_DOTENV_DISABLED=1 <python> -m pytest tests/test_rich_text.py tests/test_rich_text_link_targets.py -q: 9 passed, 2 strict known-bug failures, exit 1.
- At exact source: PYTHON_DOTENV_DISABLED=1 <python> -m pytest -q: 2202 passed, 10 existing skips, 3 failures, exit 1, 146.58 seconds. Failures are the two new cases plus tests/test_product_name.py::TestNoRetiredNameIsLeft::test_living_files_carry_no_retired_name, which flags docs/design/DESIGN.md:15,58 and docs/design/HANDOFF.md:32. This is the previously reported documentation naming defect, not infrastructure.
- Exact parent c95df5b9a30f1c3ca3e16186165d76d91102869f: PYTHON_DOTENV_DISABLED=1 <python> -m pytest tests/test_rich_text_link_targets.py -q: 2 passed, exit 0. This proves the new behavior introduced the regression; no production mutation was needed.
- Later exact d42d2df2822089448d7c0d24c3eda26ed4b2278e: PYTHON_DOTENV_DISABLED=1 <python> -m pytest tests/test_profile_theme.py tests/test_rich_text_link_targets.py -q: 20 profile tests passed, same 2 strict URL failures, exit 1. Defect remains open in latest reviewed production code.
- Ruff: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_rich_text_link_targets.py: exit 0. git diff --check: exit 0.
- Frontend at source: node node_modules/vitest/vitest.mjs run: 450 passed, exit 0; node node_modules/typescript/bin/tsc -b: exit 0. No later commit in this review changes client code.
- Later d42d2df frontend: node scripts/build-modules.mjs --check: 10 compiled blocks current, exit 0.
- Demo-brand exact 3fcdd0e485ae35e805f3814813e6013fb02264c8: PYTHON_DOTENV_DISABLED=1 <python> -m pytest tests/test_demo_reset.py -q: 17 passed, exit 0, 41.09 seconds.

No green backend/full sufficiency claim: the strict tests expose an open bug. No remaining infrastructure-blocked checks for this batch. Earlier failed invocations were corrected: nonexistent test_content_translate.py (exit 4, corrected test_content_translation.py AI run 59 passed); root cwd instead of backend for rich-text run (exit 4, corrected above); default Ruff cache sandbox EPERM (resolved with --no-cache); Backlog Git-lock EPERM (resolved by authorized elevated CLI retry).

Origin publication: succeeded, exit 0, git push origin refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. git ls-remote --heads origin refs/heads/codex/regression-tests independently confirmed c4caca9a9741fe248300c8cc7b7b5ec3cb3518cf. Pre-stage note was created, populated and read before staging, then updated with final commit/push/verification evidence. Note is separate from tests branch and is not committed by Codex.
