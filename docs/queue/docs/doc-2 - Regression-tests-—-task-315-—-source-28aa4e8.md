---
id: doc-2
title: Regression tests — task-315 — source 28aa4e8
type: other
created_date: '2026-10-09 08:38'
updated_date: '2026-10-09 08:40'
---
# Regression-test batch — task-315

Source commit covered: 28aa4e88f4846768a18fd81b66949f959cd3b38a.
Batch commit: 2a476c8acc0cfe04f9442a2dd0a75d850a91ac12.
Branch: codex/regression-tests, created directly from the source commit above.
Push: succeeded to origin; git ls-remote confirms that exact batch SHA. No changes were committed or pushed to main.

Test file modified: backend/tests/test_process_due_brand.py.
Test added: test_non_default_working_brand_fires_its_own_due_send.
It verifies that a sends.execute integration selecting a non-default brand with X-Brand fires that brand's due send, returns its ID, and neither fires nor returns the default brand's send. Existing tests primarily selected the default brand. Governing rules: ADR-172 and ADR-166.

Verification was run from /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation/backend, using the existing main-checkout backend/venv/bin/python and backend/venv/bin/ruff runtimes:
- python -m pytest -q tests/test_process_due_brand.py: all five tests passed, including the new test; exit 0.
- ruff check tests/test_process_due_brand.py: passed; exit 0.
- python -m pytest -q: full backend suite exited 0; 1530 passed, 10 existing tests skipped, one deprecation warning.
- git diff --check: passed. The batch changes only the permitted backend/tests/ file.

Strict tests failing because of an open bug: none in this batch. No skips or expected-failure markers were added. A separate in-memory test seam deliberately forced the route's sweep to use the default brand; the new test failed at its selected-send assertion with exit 1, as intended. That mutation failure proves the added test detects regression of task-315; it is not an outstanding failure on the tested source. Production source was not edited for the mutation.

Test database: app_test_newsletter_reference_implementation_17aa4d, derived from this isolated checkout. No development data or real email was used. The test replaces the send function with a recorder; live provider behavior is outside coverage. Frontend checks were not run in this batch.

## Other commits assessed in the same watcher pass

68b3589b7b9179f13c38c29a8029d50e61a23019 (task-316, task-317): existing test_login_code_races.py covers concurrent correct-code single use, atomic wrong-guess counting and exhausted-budget rejection, and equal issuance KDF work for known/unknown accounts. These three targeted tests passed. The full backend suite on this exact source exited 0 (1532 passed, 10 existing skips, one warning), in /Users/diedeslembrouck/.codex/worktrees/regression-auth-review/newsletter-reference-implementation/backend using its separate app_test_newsletter_reference_implementation_48c280 database. No additional tests were warranted for the reported invariants in this pass; no auth batch was created. This validates the intended cases, not every possible authentication interleaving or real-server latency distribution.

41684ebc57111d823903eef4151bf652f5d4c105: documentation/queue completion only; no behavior tests needed.

Integration handoff: review and cherry-pick batch 2a476c8 onto the current source when appropriate, then rerun the suite there. The tests branch intentionally remains based on 28aa4e8; the auth source was validated separately and has not been merged into it. No PR was created.
