---
id: doc-3
title: Regression tests — task-318 — source a0d06e6
type: other
created_date: '2026-10-09 08:43'
updated_date: '2026-10-09 08:45'
---
# Regression-test batch — task-318

Source commit covered: a0d06e691237a893779639a87935f051e2f8fabf.
Batch commit: 7bbe3a0a022aa1d6ae1f482c7f70ddd20c001d09.
Branch: codex/regression-tests; appended after 2a476c8 without rewriting history.
Push: succeeded to origin, independently confirmed by git ls-remote. No main commit, push, merge or PR.

File added: backend/tests/test_send_retry_consent_regression.py.
Test added: test_retry_after_unfinished_recipient_opts_out_sends_nobody.
The first provider success is committed, the second call raises, and the unfinished recipient opts out before retry. The retry must make no additional provider call, preserve the successful execution's status/message ID/delivery record, exclude the newly opted-out recipient, and report one historical success and one exclusion. This combines ADR-163's fresh consent gate with ADR-183's immutable delivery evidence. Claude's original two tests covered duplicate delivery and a later opt-out by the already-sent recipient, but not this complementary case.

## Verification against the named source

Isolated source worktree: /Users/diedeslembrouck/.codex/worktrees/regression-auth-review/newsletter-reference-implementation.
Disposable database: app_test_newsletter_reference_implementation_48c280.
Commands run from backend using the main checkout's existing backend/venv runtimes:

- python -m pytest -q tests/test_send_retry.py: both original tests passed; exit 0.
- python -m pytest -q tests/test_send_retry.py tests/test_send_retry_consent_regression.py: all three passed; exit 0.
- ruff check tests/test_send_retry_consent_regression.py: passed; exit 0.
- python -m pytest -q: full backend suite passed with exit 0 (1535 passed, 10 existing skips, one deprecation warning).

No strict test fails on a0d06e6 because of an open bug. No skips or expected-failure markers were added. No real provider or development database was used; frontend checks were not run.

## Strict failure on the tests branch's older production base

The persistent tests branch is intentionally still based on source 28aa4e8, which does not contain the task-318 fix. From that worktree root, python -m pytest -q backend/tests/test_send_retry_consent_regression.py exited 1: test_retry_after_unfinished_recipient_opts_out_sends_nobody failed because the retry mailed the already-successful recipient again. This is task-318's duplicate-send bug on that older base, not a defect remaining on tested source a0d06e6.

This red/green comparison proves the new regression detects the original behavior without mutating production source or merging fixes into the tests branch. The test stays strict. Review and integrate the batch together with the task-318 fix; do not cherry-pick it onto an unfixed main branch in isolation.

Branch lint passed with ruff check --no-cache backend/tests/test_send_retry_consent_regression.py. An initial cached Ruff invocation was blocked by the sandbox's cache-write restriction; the cache-free check succeeded. Git staged-diff validation confirmed this batch modifies only the allowed backend/tests/ file.

Additional source commit 3077ce8e392f8c2bbba336e8ff4bb738542765cd only updates queue/review documentation; no new behavior tests were needed.
