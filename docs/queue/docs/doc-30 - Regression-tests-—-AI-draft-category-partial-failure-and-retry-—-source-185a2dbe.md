---
id: doc-30
title: >-
  Regression tests — AI draft category partial failure and retry — source
  185a2dbe
type: other
created_date: '2026-10-16 20:01'
updated_date: '2026-10-17 07:06'
---
Source covered: 185a2dbeb10a4ff390ee55e3e73659eed8b7604a (task-368 client), reviewed after backend 54f4d4a9af741c2428164b54baea78e9a640b7a2. Documentation-only 4d61b8d645210544171914cd11d2314a9a3aaea9 reviewed separately; no tests needed. No rewrite from cddcde13.
Tests-branch batch commit: 3d4a4d9c67715a30df8e1fb3741c25b73ade2e07. Previous local and origin tip: 836cad5be589a4ee46496861a5a23ba65cf89717.
New test file: frontend/src/screens/ContentDraft.partial-failure.test.tsx.
Invariant (ADR-141 addendum 2026-10-16 points 5-6; ADR-080): after one category saves and the next returns 503, show the refusal without claiming all succeeded, retain the first saved category, then retry against its current assignment id rather than POSTing a duplicate. Verify every retry carries the score and AI run id. Uses existing stubFetch/renderWithProviders/jsonResponse fixtures; all HTTP intercepted. The test passes on current code; no open defect exposed, and no task-315 through task-323 mapping. Existing happy-path tests did not cover this partial failure/retry. No production fix changed; earlier source has no ContentDraft panel, so an earlier broken implementation comparison is not applicable.

Exact-source validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-admin-fixed/newsletter-reference-implementation. First detached at exact 54f4d4a9 for backend checks, then exact 185a2dbe for client checks. backend/.env absent, dotenv disabled, no TEST_DATABASE_URL override; disposable PostgreSQL app_test_newsletter_reference_implementation_3190ed, backend runs serialized. Existing mock providers and suite-wide real-vendor refusal guard; no real email/model call, source checkout or shared dependency changes. Dependency symlink only in isolated worktree.

Backend commands at 54f4d4a9, from backend with PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python:
- -m pytest tests/test_content_draft.py tests/test_applied_suggestion.py -q: 21 passed, exit 0; /private/tmp/regression-content-draft-target.log.
- -m pytest tests -q: 2116 passed, 10 existing skips, exit 0, 85.94s; /private/tmp/regression-content-draft-backend-full.log.
Ruff check --no-cache on backend/app/ai, changed content/settings/campaign/auth modules and content-draft/settings tests: exit 0. TypeScript -b at backend-only snapshot: exit 0.
Contract: dotenv-disabled Python exported main.app.openapi() after setting DATABASE_URL=tests.checkout_database.test_database_url(), to /private/tmp/regression-content-draft-openapi.json, exit 0. From frontend, node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-content-draft-openapi.json -o /private/tmp/regression-content-draft-schema.d.ts; diff -u src/api/schema.d.ts /private/tmp/regression-content-draft-schema.d.ts: exit 0, identical. No tracked generated file written. git diff --quiet 54f4d4a9 185a2dbe -- backend frontend/src/api/schema.d.ts: exit 0; backend/contract unchanged in client commit, not rerun as if new backend validation.
Client commands at exact 185a2dbe from frontend:
- node node_modules/vitest/vitest.mjs run src/screens/ContentDraft.partial-failure.test.tsx src/screens/ContentDraft.test.tsx src/screens/Settings.test.tsx: 24 passed, exit 0; /private/tmp/regression-content-draft-client-target.log.
- node node_modules/vitest/vitest.mjs run: 363 passed, exit 0; /private/tmp/regression-content-draft-client-full.log.
- node node_modules/typescript/bin/tsc -b: exit 0 after a test-fixture typing correction (stubFetch's declared response type required the existing async-fixture cast convention; no assertion/behavior changed).
- node node_modules/eslint/bin/eslint.js src/screens/ContentDraft.partial-failure.test.tsx src/screens/ContentDraft.tsx src/screens/ContentDraft.test.tsx src/screens/ContentDetail.tsx src/screens/Settings.tsx src/api/resources.ts: exit 0.
- Final new test rerun after that type-only adjustment: node node_modules/vitest/vitest.mjs run src/screens/ContentDraft.partial-failure.test.tsx: 1 passed, exit 0; /private/tmp/regression-content-draft-retry-final.log.
No remaining infrastructure failure or known-bug test failure. Existing Starlette/Vite warnings only. Bounded coverage sufficient for this reviewed behavior; actual model output and browser rendering were not independently verified. URL fetching remains an explicit decision task-388, and server concurrent-AI suppression remains task-387.

Persistent codex/regression-tests retains old production base 28aa4e88f4846768a18fd81b66949f959cd3b38a and all earlier batches; no production history merged. ContentDraft is absent on that base: the above results validate the exact intended source snapshot, not collection or a passing suite on the older branch base. This one permitted test file awaits integration. Origin push: succeeded, explicit refs/heads/codex/regression-tests:refs/heads/codex/regression-tests push; git ls-remote verified 3d4a4d9c67715a30df8e1fb3741c25b73ade2e07. Normal commit hooks were not bypassed. Primary note stays outside test commits.

Integration verification — 2026-10-17
Source b18eadd8a415d7aa1126aadb0513902d28794c31 integrates frontend/src/screens/ContentDraft.partial-failure.test.tsx from published 3d4a4d9c67715a30df8e1fb3741c25b73ade2e07 byte-for-byte unchanged. Reviewed as its own commit after previous cursor 4d61b8d6; no history rewrite. This batch no longer awaits integration.
Exact committed snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-draft-integrated/newsletter-reference-implementation, detached at b18eadd8. No source/test edits; read-only existing frontend dependencies through a symlink. Existing fixtures intercept all requests; no database, real provider, email or .env used.
From snapshot/frontend:
- node node_modules/vitest/vitest.mjs run src/screens/ContentDraft.partial-failure.test.tsx: 1 passed, exit 0; /private/tmp/regression-draft-integrated-target.log.
- node node_modules/vitest/vitest.mjs run: 363 passed, exit 0, 9.72s; /private/tmp/regression-draft-integrated-full.log.
- node node_modules/typescript/bin/tsc -b: exit 0.
- node node_modules/eslint/bin/eslint.js src/screens/ContentDraft.partial-failure.test.tsx: exit 0.
Backend and frontend API files are identical to the earlier validated 185a2dbe source (git diff --quiet 185a2dbe b18eadd8 -- backend frontend/src/api, exit 0); no new backend/schema run claimed. No meaningful remaining gap for this test-only integration; no new test batch, commit or push needed. No infrastructure failure. Shared checkout's uncommitted translation work was not edited or used for validation.
