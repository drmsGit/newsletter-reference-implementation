---
id: doc-10
title: Regression tests — withdrawal stays final — source 7ceb903
type: other
created_date: '2026-10-10 20:03'
updated_date: '2026-10-10 21:01'
---
Source commit: 7ceb9036c66b4cc989e1b8eef6c39db390964dec (task-331).
Tests-branch batch commit: 6ae93bb9457167e2192f8d740d24d6d2f6b439c0, parent 35b31c87ab9f5e8d2624f5e081b01c3ee2978feb. Only backend/tests/test_requester_withdrawal_finality.py changed (45 lines).
Added file: backend/tests/test_requester_withdrawal_finality.py.
Invariant: an integration switched off or stripped of sends.execute causes withdrawal; restoring that access cannot revive the request, deliver mail, or create a second withdrawal audit. ADR-142 second 2026-10-09 addendum.
Exact validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-integrated/newsletter-reference-implementation, pinned to source above.
Tests branch retains earlier production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and all previous batches; validation here is against the intended newer source, not that older branch base.
Commands (backend cwd, shared existing backend/venv/bin/python; PYTHON_DOTENV_DISABLED=1):
- python -m pytest -q tests/test_requester_standing.py tests/test_requester_withdrawal_finality.py: 11 passed, exit 0.
- python -m pytest -q tests: 1626 passed, 10 existing skips, exit 0.
- ruff check --no-cache backend/tests/test_requester_withdrawal_finality.py: passed, exit 0 (snapshot root).
Frontend cwd: node node_modules/vitest/vitest.mjs run: 236 passed, exit 0. node node_modules/typescript/bin/tsc -b: exit 0. OpenAPI exported directly from isolated main.app to /tmp/task331-openapi.json, generated with openapi-typescript into /tmp/task331-schema.d.ts and diffed against source schema.d.ts: identical, exit 0; no live server used.
Disposable test database app_test_newsletter_reference_implementation_0f33c8 confirmed separate from development; no TEST_DATABASE_URL override, no .env present in snapshot, vendor HTTP guard and mock send fixture active.
Known open-bug failures tasks 315-323: none observed in this batch.
Infrastructure/unverified: GitHub's actual scheduled run and scanner container have not been executed locally.
Origin push outcome: SUCCESS, exit 0; git push origin refs/heads/codex/regression-tests:refs/heads/codex/regression-tests; git ls-remote verified 6ae93bb9457167e2192f8d740d24d6d2f6b439c0. Pending human/Claude integration; no main changes or PR.


Mutation proof: PYTHONPATH=/tmp PYTHON_DOTENV_DISABLED=1 backend/venv/bin/python -m pytest -q -p task331_finality_mutation tests/test_requester_withdrawal_finality.py (backend cwd, shared absolute interpreter): 2 failed, exit 1, at the second approval assertion, with an actual mock delivery. Runtime-only plugin reopens withdrawn rows; no production file changed. This expected mutation failure is not an open bug in the source.
Older tests-branch base does not contain task-331 production changes or tests/test_requester_standing.py fixture helpers; this batch must be integrated after task-331. The tests branch itself is not claimed green.


Exact final commands, backend cwd in source worktree:
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_requester_standing.py tests/test_requester_withdrawal_finality.py
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests
PYTHONPATH=/tmp PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q -p task331_finality_mutation tests/test_requester_withdrawal_finality.py
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_requester_withdrawal_finality.py
Last command rechecked unmodified source after mutation: 2 passed, exit 0.
Source-root Ruff: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_requester_withdrawal_finality.py (exit 0).
Contract check used export from main.app.openapi() without startup to /tmp/task331-openapi.json; frontend commands: node node_modules/openapi-typescript/bin/cli.js /tmp/task331-openapi.json -o /tmp/task331-schema.d.ts; diff -u src/api/schema.d.ts /tmp/task331-schema.d.ts (both exit 0).
Sufficiency: focused task-331 access-restoration/withdrawal-finality gap covered, source backend and frontend suites green with 10 pre-existing backend skips. No claim of exhaustive architecture coverage or a green older tests-branch base.

Other chronological commit reviews this wake:
62c327f8022ebd4ba964488022b567f7cedc9197: vendor-guard target 4 passed/1 failed, exit 1 because absent key prevented reaching guard. Superseded by follow-up 015bfd3eaab9dc925bad21da20d6801e524fd6cb: target 5 passed; backend full 1608 passed/10 existing skips, exit 0.
ef81dc4f3c9de2bd24aee818ed6cf3000940314c: unsubscribe base URL target 7 passed; full 1615 passed/10 existing skips, exit 0.
5024cd910bd51eab1d4f9fa150ae747748f89f1a: documentation only, reviewed, tests not needed.
96501992bd95d38827509ae13a7569ee7dc98eac: documentation only, reviewed, tests not needed.
8eb7fb64d9d9dde19416ca5ef53d7c4ea4e49bd1: CI workflow target 3 passed; full 1627 passed/10 existing skips, exit 0; actual hosted schedule/container execution unverified.
64acc2a05d090e0ba49d5e863dc75d8f6f7e49fe: documentation only, reviewed, tests not needed.
d27b09fc3473c19a33f07b8b4a3d5a27b8b524ca: query retry target 12 passed; frontend full 248 passed and typecheck exit 0; existing behavioral tests sufficient for changed retry policy, no additional batch.


Integration verified 2026-10-10: 2f18e2860c2c04389a44ece841d04f0015e50e3a imports the made fixture directly; test bodies and strict assertions preserved. Isolated regression-send-outcome worktree pinned to that commit: targeted tests/test_requester_withdrawal_finality.py 2 passed, exit 0; backend full tests 1642 passed, 10 existing skips, exit 0. Both commands used PYTHON_DOTENV_DISABLED=1 and the shared absolute backend/venv/bin/python, backend cwd, database app_test_newsletter_reference_implementation_32f1fd. The previous batch is integrated and independently verified.
