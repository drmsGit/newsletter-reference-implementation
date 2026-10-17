---
id: doc-15
title: Regression tests — profile link attribution boundary — source ad46272f
type: other
created_date: '2026-10-11 11:03'
updated_date: '2026-10-11 12:02'
---
Source commit: ad46272f94dfee58ed8b029e56e772a2a11364b2 (task-351 header/footer, using task-354 link tagging introduced at 8e70ea78664db84d3587be174f0a7d25ed2dde20).
Tests-branch batch commit: c6af95c9b64fb028244585f383de5ed197e3fb02. Origin push succeeded (aa7cc03 -> c6af95c), independently confirmed by git ls-remote origin refs/heads/codex/regression-tests. Only backend/tests/test_profile_link_attribution_boundary.py changed, byte-for-byte matching the exact-source validation file.
Added file: backend/tests/test_profile_link_attribution_boundary.py.
Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-profile-look/newsletter-reference-implementation, pinned to the exact source above.
Database isolation confirmed before testing: app_test_newsletter_reference_implementation_3e5be9, different from development database; no explicit shared TEST_DATABASE_URL, backend/.env absent. No .env read and no real providers called. Existing conftest provider guard applies.

Invariant (ADR-182 point 3; ADR-194 third and fourth addenda): profile analytics extras must not attribute non-content links. Header/footer links never receive the content-attribution parameter. Ordinary utm_source and ref tags still appear.
The three strict cases render actual CTA/header/footer HTML into an email and parse outbound links. Previously stored extras nl_content=424242 currently produce that marker on all three non-content module types; content_id_from_url would identify 424242. This defect is associated with task-354 and task-351, not task-315 through task-323. No new accepted bug task was created or changed.
No production changes or skip/xfail/weakening. The test exercises previously stored values as well as current rendering, so relying only on a future save-time rejection would leave the rendering boundary unprotected.
Sufficiency: risk-focused coverage; no passing-suite or overall sufficiency claim while the new strict failures remain.

Exact commands and results (backend or frontend cwd of the snapshot):
- At 8e70ea78664db84d3587be174f0a7d25ed2dde20: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_profile_theme.py tests/test_brand_profile_structure.py: exit 0, 27 passed.
- At 98b6d29c4ff3417e663e069a68a75dcb0aef61f6: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_brand_profile_default_state.py: exit 0, 1 passed. node node_modules/vitest/vitest.mjs run src/screens/BrandProfileRefresh.test.tsx src/screens/BrandProfiles.test.tsx: exit 0, 10 passed. Both tests from aa7cc036bd78f79525917a1c0f5b30d75f977357 were integrated byte-for-byte with fixes; no pending integration for that batch.
- At exact source ad46272f: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_header_footer.py tests/test_profile_theme.py tests/test_envelope_frame_boundaries.py: exit 0, 35 passed.
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_profile_link_attribution_boundary.py --tb=short: exit 1, all 3 parametrized cases failed on nl_content unexpectedly present (CTA, header, footer).
- PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests --tb=short: exit 1; 1768 passed, 3 failed, 10 skipped, in 69.05s. Only the three new attribution cases failed.
- node node_modules/vitest/vitest.mjs run: exit 0, 263 passed.
- node node_modules/typescript/bin/tsc -b: exit 0.
- /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_profile_link_attribution_boundary.py: exit 0.
- git diff --check: exit 0.

Infrastructure/unverified: no infrastructure failures so far. Remote CI not inspected.
The persistent codex/regression-tests branch retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a; no production merged. It lacks the profile modules/fixtures needed by this batch. Results above are against intended source ad46272f, not the older tests-branch base. Earlier batches preserved.
Integration: new strict tests await the corresponding production fix; they should land together so main is not made red.

API contract verification: export main.app.openapi() with DATABASE_URL set to tests.checkout_database.test_database_url(), then node node_modules/openapi-typescript/bin/cli.js /private/tmp/profile-look-openapi.json -o /private/tmp/profile-look-schema.d.ts && diff -u src/api/schema.d.ts /private/tmp/profile-look-schema.d.ts: both exit 0, generated contract matches.


Integration verified 2026-10-11: e486157c0e996ea6e4cbceba6435a76a3c8100d9 contains backend/tests/test_profile_link_attribution_boundary.py byte-for-byte from c6af95c9b64fb028244585f383de5ed197e3fb02 with the production fix. At that exact isolated snapshot, PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_profile_link_attribution_boundary.py tests/test_profile_theme.py passed 21 tests, exit 0. This batch no longer awaits integration.
