---
id: doc-20
title: Regression tests — ranked-set changes and frozen sends — source a407b127
type: other
created_date: '2026-10-11 19:58'
updated_date: '2026-10-15 20:03'
---
Source commit: a407b127dde793e646dcaef72ff88d5e082b41bb (task-109).
Tests-branch batch commit: 6d3769498d1df317a484759ecaf3d516c365be35; previous tip 2b74143b82441e3e4d548d3088d55fb75e330e42.
Added file: backend/tests/test_ranked_picks_frozen_safety.py (two parametrized behavioral cases).
ADRs: ADR-084 addendum 2026-10-11 and ADR-183. A three-pick set shrunk to one or exhausted must not leak stale copies into the next send; the first delivery record, reconstructed body/modules and hash stay unchanged.

Validation snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-results-picks/newsletter-reference-implementation, detached at full source above. Disposable PostgreSQL database app_test_newsletter_reference_implementation_99648d; no test-database override or .env, suites serialized; real AI/email adapters blocked by conftest and mock delivery provider used.

Exact commands from snapshot backend:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_ranked_picks_frozen_safety.py tests/test_several_picks.py -q: 19 passed, exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests -q: 1899 passed, 10 existing skips, exit 0 (81.08s).
From snapshot root:
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_ranked_picks_frozen_safety.py: exit 0.
From snapshot frontend:
- node node_modules/vitest/vitest.mjs run: 275 passed, exit 0.
- node node_modules/typescript/bin/tsc -b: exit 0.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python (export main.app.openapi() after setting DATABASE_URL=tests.checkout_database.test_database_url()) to /private/tmp/regression-results-picks-openapi.json; node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-results-picks-openapi.json -o /private/tmp/regression-results-picks-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/regression-results-picks-schema.d.ts: both exit 0, no difference.

Runtime-only fault probes in the same isolated source, using Python pytest.main(..., plugins=[Probe()]) with pytest autouse monkeypatch, no production file changes: suppress Session.delete for DecisionResolutionDB, run -k shrink: exit 1, assertion observed three picks instead of one; clear render_frame empty_slots, run -k exhaust: exit 1, assertion observed stale picks instead of none. Both failures are intentional mutant detections, not open source defects. These are fault-injection checks, not validation on the pre-feature parent, whose tests lack the ranked-set fixtures.

Open-bug failures on intended source: none; targeted and full suites pass. Scoped coverage strengthened; not an exhaustive audit. No task-315 through task-323 defect claimed. Infrastructure failures: none. Legacy upgrade migrations 0048/0049 unverified; suite rebuilds from current models.

Persistent codex/regression-tests production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a, without merging newer production. This file uses test_several_picks fixtures absent at that base; no claim it collects/passes there. Intended-source results above must not be confused with old-base validation. Earlier test batches preserved.

Origin push: succeeded (exit 0), explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests, independently verified ls-remote equals 6d3769498d1df317a484759ecaf3d516c365be35. Commit changes only backend/tests/test_ranked_picks_frozen_safety.py, parent is the previous tests-branch tip; working tree clean. Integration: pending, never automatically copied into Claude's shared checkout. This pre-stage note is separate and will not be included in the test commit.

## Integration verified 2026-10-15

Both batches 6d3769498d1df317a484759ecaf3d516c365be35 and d7051b827e5b048dfdfc3726682f123228314181 were integrated byte-for-byte in source e0a30ed0bf11e533d82f671a0ceecd56e09b62f7. In isolated worktree /Users/diedeslembrouck/.codex/worktrees/regression-send-assets/newsletter-reference-implementation pinned to that source, unique disposable database app_test_newsletter_reference_implementation_e7ad62, this command from backend passed (exit 0):
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest tests/test_hand_binding_snapshot_safety.py tests/test_ranked_picks_frozen_safety.py -q
Result: 3 passed. No integration pending for either batch. These intended-source results do not claim a green suite on the older tests branch production base. Original pushes remain verified successful.
