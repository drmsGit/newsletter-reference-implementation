---
id: doc-4
title: Regression tests — task-319 — source c06f1ba
type: other
created_date: '2026-10-09 08:50'
updated_date: '2026-10-09 08:51'
---
# Regression-test batch — task-319

Source commit: c06f1bace31f81ad750658ea9f869bf43891a47a.
Batch commit: 148bfb5ee33edf1b742b101194354cddb9091a2f.
Branch: codex/regression-tests, appended after 7bbe3a0.
Push succeeded to origin; git ls-remote confirmed the exact SHA. No main commit/push, production merge or PR.

File added: backend/tests/test_webhook_signal_rollback.py.
Test added: test_failure_after_signal_write_rolls_back_event_and_retries_once.
A named-content click writes a real signal contribution, then a simulated RuntimeError interrupts processing. The handler must roll back both event and contribution without caller cleanup. Retrying must create one event and one correctly linked email contribution; another delivery of that event must be duplicate and create nothing. This covers the signal side of task-319's new transaction boundary beyond the existing complaint/consent tests (ADR-132, ADR-182).

## Passing checks on the source snapshot

Worktree: /Users/diedeslembrouck/.codex/worktrees/regression-webhook/newsletter-reference-implementation.
Database: app_test_newsletter_reference_implementation_ec554b.
Commands used the existing primary backend/venv runtimes from the isolated backend directory:

- python -m pytest -q tests/test_webhook_effects.py tests/test_click_attribution.py: six passed; exit 0.
- python -m pytest -q tests/test_webhook_effects.py tests/test_click_attribution.py tests/test_webhook_signal_rollback.py: seven passed; exit 0.
- ruff check tests/test_webhook_signal_rollback.py: passed; exit 0.
- python -m pytest -q: full backend suite exited 0 (1537 passed, 10 existing skips, one deprecation warning).
- Branch ruff check --no-cache backend/tests/test_webhook_signal_rollback.py and staged diff/path checks passed.

No strict test fails because of an open bug on c06f1ba plus this batch. The failure injected inside the test is required by its regression scenario, and its expected exception is an ordinary assertion, not an expected-failure marker. No skips or xfails were added.

## Failure on the older tests-branch base

The persistent tests branch remains based on 28aa4e8 and does not contain the task-319 production fix. From its worktree root, python -m pytest -q backend/tests/test_webhook_signal_rollback.py exited 1: the new test found the engagement event still persisted after the interrupted signal write. This exposes task-319 on that older base and proves the regression distinguishes broken from fixed behavior. Keep it strict and integrate with the task-319 fix. It does not indicate a remaining defect on source c06f1ba.

No production source was modified to obtain the red/green comparison. Tests used isolated disposable databases and no real email. No frontend tests or live webhook transport were exercised; concurrent delivery of duplicate events was not stress-tested.

## Integration commits assessed

8a824aba19bdb9bf38144f434a51f96da43bd79e: reviewed the task-315 test integration; five scheduler tests passed on that exact source.
93c0ea3082da80a2536cf0ca2621ea83b49a9a43: reviewed the task-318 test integration; both integrated test files passed together (six tests). The full backend suite on this exact integrated snapshot exited 0 (1538 passed, 10 existing skips, one warning). It includes the preceding integration commit, but is not a separate full-suite execution at 8a824ab.

Integration checks used /Users/diedeslembrouck/.codex/worktrees/regression-integrated/newsletter-reference-implementation with its own app_test_newsletter_reference_implementation_0f33c8 database. No duplicate tests were added for those integration commits.

Review and cherry-pick 148bfb5 onto source carrying the task-319 fix, then rerun the suite in that final context. Earlier batches remain preserved on the tests branch.
