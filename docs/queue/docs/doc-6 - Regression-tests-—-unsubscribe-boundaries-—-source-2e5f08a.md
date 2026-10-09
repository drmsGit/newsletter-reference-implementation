---
id: doc-6
title: Regression tests — unsubscribe boundaries — source 2e5f08a
type: other
created_date: '2026-10-09 13:21'
updated_date: '2026-10-09 13:25'
---
Source: 2e5f08aac40a49f14c8dc9f6850d21a8c4dfa860 (task-56 unsubscribe).
Tests-branch batch: 2b329ee32aafc8621da001beed03e1e6707330ae; push to origin/codex/regression-tests succeeded, remote SHA verified.
Added file: backend/tests/test_unsubscribe_boundaries.py (two tests).
- Default opt-out changes only the sending brand/email/marketing cell; it preserves push consent, transactional consent, sibling-brand consent and another recipient.
- A failure after two consent writes in "everything" leaves no partial opt-outs; retry completes all brand/channel marketing cells, preserves transactional consent and repeated submission writes no further events.
Governing decisions: ADR-191, ADR-163. ADR-191 was read from the live repository; its documentation commit fd97368 follows the feature source and is not part of the pinned 2e5f08a snapshot.

Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-unsubscribe/newsletter-reference-implementation.
Disposable database: app_test_newsletter_reference_implementation_d45a9d. Mock providers only, no development database or real email.
Commands below run from the snapshot's backend directory, using /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python:
- -m pytest -q tests/test_unsubscribe.py tests/test_resend.py: 16 passed, exit 0.
- -m pytest -q tests/test_unsubscribe_boundaries.py tests/test_unsubscribe.py tests/test_resend.py: 18 passed, exit 0.
- -m pytest -q tests: 1569 passed, 10 existing skips, exit 0. The first execution session expired before its final result could be read; this is the completed recovery run, saved in /private/tmp/unsubscribe-source-suite.log.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache tests/test_unsubscribe_boundaries.py: passed.
- Mutation: PYTHONPATH=/private/tmp:. python -m pytest -q -p regression_unsubscribe_mutation tests/test_unsubscribe_boundaries.py::test_everything_failure_rolls_back_all_cells_then_retry_is_idempotent: 1 failed as expected, exit 1, because two premature commits remained after the injected failure. Temporary pytest plugin only; production files unchanged.

On the persistent tests branch, whose production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a, the targeted file has two setup errors (exit 1): unsubscribe_token does not exist yet. These are unavailable-feature errors on the old base, not open bugs on the intended source and not task-315 through task-323 failures. Assertions were not skipped or weakened. Production history was not merged into the tests branch. An initial root-directory invocation selected the wrong relative path (exit 4, no tests); the backend-directory run above is the actual compatibility result.

No infrastructure failures remain for source backend validation. Frontend suite and generated-client contract check were not run. Existing Starlette deprecation warning remains. Apply the test-only batch with task-56's implementation, not alone onto a pre-feature production base; integration by Claude is pending.
