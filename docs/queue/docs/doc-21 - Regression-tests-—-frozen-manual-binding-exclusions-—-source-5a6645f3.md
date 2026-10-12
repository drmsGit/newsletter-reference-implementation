---
id: doc-21
title: Regression tests — frozen manual binding exclusions — source 5a6645f3
type: other
created_date: '2026-10-11 20:49'
updated_date: '2026-10-11 20:51'
---
Source: 5a6645f3b441d93347bd452183f720448defd4c9 (task-220).
Tests-branch batch commit: d7051b827e5b048dfdfc3726682f123228314181; previous tip 6d3769498d1df317a484759ecaf3d516c365be35.
Added file: backend/tests/test_hand_binding_snapshot_safety.py.
ADRs: ADR-176 addendum 2026-10-11 and ADR-183. Slot exclusions must use hand-placed records from the approved frame, even when the live manual binding changes before sending. The test approves A, changes the live binding to B, and verifies the send picks B/C and reconstructs B/C/A with matching hash.

Isolated worktree: /Users/diedeslembrouck/.codex/worktrees/regression-results-picks/newsletter-reference-implementation, pinned to the exact source above. Disposable PostgreSQL database app_test_newsletter_reference_implementation_99648d; no TEST_DATABASE_URL override, no .env present/read; backend suites serialized. Existing network refusal guard and mock send provider used, no real email.

From snapshot backend, exact commands:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_hand_binding_snapshot_safety.py tests/test_hand_beats_slot.py tests/test_render_skip.py tests/test_several_picks.py tests/test_ranked_picks_frozen_safety.py -q: 35 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_hand_binding_snapshot_safety.py -q at parent d84d5d2b43ba4d1784ff879d797d0b192f331836: 1 failed, exit 1, expected distinguishing failure: picks A/B rather than B/C. This is pre-fix behavior, not an open defect on the intended source.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q at intended source: 1904 passed, 10 existing skips, exit 0 (71.17s).
From snapshot root:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_hand_binding_snapshot_safety.py: exit 0.

Open-bug failures on intended source: none; targeted and full backend suites passed. Coverage is sufficient for this scoped review after the addition, not an exhaustive audit. No task-315 through task-323 defect claimed. Infrastructure failures: none. No frontend code or API schema shape changed in source; frontend suite not rerun. Legacy migration upgrades unverified, backend suite rebuilds from models.

Persistent codex/regression-tests retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and all previous test batches. This test uses ranked-pick fixtures absent on that old base; intended-source passing validation above is not validation against the older tests-branch base. No production merged into the tests branch.

Origin push: succeeded, exit 0, explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests; independently verified ls-remote equals d7051b827e5b048dfdfc3726682f123228314181. Commit changes only the allowed backend/tests/test_hand_binding_snapshot_safety.py; its parent is the previous tip and worktree is clean. Integration pending for this batch and earlier 6d376949; no automatic copying to shared checkout. This note is separate from the tests branch and will not be committed in the batch.
