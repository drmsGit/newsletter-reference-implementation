---
id: doc-7
title: Regression tests — task-318 repeated uncertain retry — source b8ac882
type: other
created_date: '2026-10-09 13:27'
updated_date: '2026-10-09 14:07'
---
Source commit: b8ac88258db5e054ced30f54f11a729e358a4f6d (task-318 AC #3).
Tests-branch batch: 21e1b1955ba184991c2cf763fbdc9b699a7450f7; pushed successfully to origin/codex/regression-tests, remote SHA verified.
Added file: backend/tests/test_uncertain_repeated_retry.py.
Two parametrized cases: all deliveries uncertain, and one known success plus one uncertain delivery.

Verified remaining task-318 defect:
1. The mock provider accepts the final message, then raises because its response was lost.
2. The first retry turns the durable "sending" execution into "uncertain" and calls the provider for nobody.
3. The next retry calls the provider again for that uncertain recipient. Both new cases fail at "a later retry contacted the uncertain recipient".
The loop skips "sent" and handles "sending" but does not skip an execution already "uncertain". A known uncertain outcome therefore becomes retryable on a later run, violating the task's recorded user decision ("never risk a duplicate"). This is a remaining defect even though task-318 is marked Done; no accepted task or production file was edited. Governing context: task-318's recorded policy, ADR-183 delivery evidence, ADR-163 consent; relevant repository instructions were read in the snapshot.

Source validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-uncertain-retry/newsletter-reference-implementation.
Disposable PostgreSQL database: app_test_newsletter_reference_implementation_e01398, separate from other suites and development. Mock providers only.
Exact commands run from the worktree's backend directory with /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python:
- -m pytest -q tests/test_uncertain_repeated_retry.py tests/test_send_uncertain.py tests/test_send_retry.py tests/test_send_retry_consent_regression.py: 2 failed (new repeated-retry cases), 6 passed, exit 1. Log: /private/tmp/uncertain-targeted.log.
- -m pytest -q tests: 2 failed (same new cases), 1570 passed, 10 existing skips, exit 1. Log: /private/tmp/uncertain-source-suite.log.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache tests/test_uncertain_repeated_retry.py: passed.

Assertions remain strict, with no skip or expected failure. No green-suite or sufficiency claim is made. On the persistent tests branch's older production base 28aa4e88f4846768a18fd81b66949f959cd3b38a, the same targeted file also fails both cases earlier because the pre-call "sending" marker does not exist. That result does not replace the exact-source reproduction above. Earlier test batches and production history were preserved; production changes were not merged.

No infrastructure-blocked source backend checks. Frontend/client-contract suite not run; generated status-filter metadata reviewed, not execution-verified. Starlette deprecation warning remains.
Claude should review and integrate this strict batch together with the task-318 fix, never alone onto main. The test reproduces the missing guard; production repair and integration are pending. Codex did not send messages to any other chat or application.

## Follow-up verification — 2026-10-09

Claude integrated both published test batches unchanged: 5b5fa911566ca9f3739a7c5c5ed0d9ccc7b40b53 (unsubscribe boundaries) and 7bcaf4bc6a72a4ab4e67121f82f581ae566a4b04 (strict repeated retry). On exact integration snapshot 7bcaf4b, the combined targeted tests had 2 failed / 2 passed; the full backend had 2 failed / 1572 passed / 10 existing skips, exit 1. Both failures were the task-318 repeated-retry cases.

Claude then fixed the missing UNCERTAIN skip in 1164f53b1618f76692932989043a6c938166ad09. The same strict tests now pass without modification. Validation reused the clean managed worktree /Users/diedeslembrouck/.codex/worktrees/regression-new-batches-integrated/newsletter-reference-implementation, checking out that exact fix commit after the earlier suite completed. Its separate disposable database is app_test_newsletter_reference_implementation_f659ff.

From that worktree's backend directory, using /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python:
- -m pytest -q tests/test_uncertain_repeated_retry.py tests/test_send_uncertain.py tests/test_send_retry.py tests/test_send_retry_consent_regression.py tests/test_unsubscribe_boundaries.py: 10 passed, exit 0.
- -m pytest -q tests: 1574 passed, 10 existing skips, exit 0. Logs: /private/tmp/uncertain-fixed-targeted.log and /private/tmp/uncertain-fixed-suite.log.

The remaining task-318 defect documented above is therefore repaired on 1164f53, and both test batches are integrated by Claude. Historical source failures and the persistent tests branch's old-base limitations remain recorded above. Codex did not merge into or push main.
