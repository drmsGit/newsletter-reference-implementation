---
id: doc-12
title: Regression tests — envelope frame boundaries — source 0d2ef147
type: other
created_date: '2026-10-10 23:03'
updated_date: '2026-10-11 08:59'
---
Source commit: 0d2ef14723a461183aabca206b28583276eaa68d (task-349).
Documentation follow-up reviewed separately: 86747ad72e3a9a8eae62505642e16b519a47fc05; no test commit for documentation.
Tests-branch batch commit: 964d51ea7e0490795f40a6540d6f51dfd9aa58f9; this note was created and read back before staging. Parent 0cbd54050f832682e021ea2b67458f0db34e82b7; previous batches preserved.
Added: backend/tests/test_envelope_frame_boundaries.py (five behavioral cases).
ADRs: 183 and 193; required-field behavior also follows ADR-174.

Coverage: introducing a visible header cannot change the bytes/hash, module marker, frozen values or envelope-only floor of a version-1 email; version-2 header selects its own template and required fields. Actual migration 0043 renames only live email rows, preserves frozen snapshot JSON and other channels, leaves other module data intact, and is repeatable. Visible header is a synthetic lookup fixture because task-351 remains future work; no production manifest or template was installed.

Exact validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-neutral-prompt/newsletter-reference-implementation at the full source SHA above.
Backend cwd: that worktree/backend. Runtime: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python.
Isolation checked without reading any .env: snapshot backend/.env absent, TEST_DATABASE_URL absent, derived disposable database app_test_newsletter_reference_implementation_045474 differs from development. No concurrent suite shares it. Mock/provider refusal guards remain in place.

Commands and observed results:
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_envelope_frame_boundaries.py tests/test_envelope_rename.py tests/test_frame.py tests/test_render_skip.py: 40 passed, exit 0.
- PYTHONPATH=/tmp PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q -p envelope_gate_mutant tests/test_envelope_frame_boundaries.py: 2 failed, 2 passed, exit 1 before migration case was added. Temporary runtime mutation translates every header to envelope regardless of version. Expected mutation failures: version-2 visible template and version-2 required logo. These are sensitivity proof, not source defects; no production file was modified.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests: 1663 passed, 10 existing skips, exit 0 in 58.84s.
- From snapshot frontend: node node_modules/vitest/vitest.mjs run: 30 files, 250 tests passed; followed by node node_modules/typescript/bin/tsc -b: combined command exit 0. Dependencies reused via local symlink, without installation.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_envelope_frame_boundaries.py: passed, exit 0.
- git diff --check: passed, exit 0.

Known-bug failures: none observed against the intended source; none mapped to tasks 315-323.
Infrastructure/unverified: initial sandboxed ls-remote failed DNS; approved retry succeeded and confirmed origin tests branch at 0cbd54050f832682e021ea2b67458f0db34e82b7. Full backend, targeted tests, frontend suite and typecheck verified; publication verified.
Persistent branch retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a. No production merge will be made. Source validation above is not validation against that older base, which lacks migration 0043 and the rename.
Integration pending: authorized publication only; Claude's shared checkout will not be edited or staged.
Origin push: SUCCEEDED, exit 0, using git push origin refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. git ls-remote origin refs/heads/codex/regression-tests confirmed 964d51ea7e0490795f40a6540d6f51dfd9aa58f9. Commit paths checked: only backend/tests/test_envelope_frame_boundaries.py; branch clean. Normal commit hooks were not bypassed.

Assessment: meaningful rename/version-collision and migration gaps covered; the relevant full suites passed on the intended source. This does not validate task-351's future production header or legal footer/theme implementation.


## Integration verified 2026-10-11

Batch 964d51ea7e0490795f40a6540d6f51dfd9aa58f9 was integrated unchanged in 779db717e5d77d0ad3e54f0412b1838d3859e6d0: targeted five tests passed on the isolated derived database. The original substring guard was subsequently found too narrow for CI's app_ci_test name; local passing results above did not establish CI compatibility. Independently reproduced on checkout-specific app_ci_671181_test: predecessor 4 passed / 1 guard failure, exit 1. Source ba1e8461ed141864b3c3c834c2b0ce1818118192 fixes the test guard without weakening behavior: same CI-style probe 5 passed, exit 0; full backend 1663 passed, 10 existing skips, exit 0. Actual remote CI status was not inspected. Validation worktree /Users/diedeslembrouck/.codex/worktrees/regression-envelope-ci/newsletter-reference-implementation. The correction is already integrated on the source branch; doc-13 records its preservation on codex/regression-tests. No integration remains pending for this batch.
