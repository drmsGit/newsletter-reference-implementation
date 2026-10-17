---
id: doc-33
title: Regression tests — approval request state isolation — source ff2cbfb
type: other
created_date: '2026-10-17 12:09'
updated_date: '2026-10-17 13:04'
---
Source: ff2cbfb19976e68ee21f0b3124f7f90781ff0a05 (task-372, approvals split view).
Tests-branch batch commit: dcdade9c4f0f95ff1f9e1bb3761efe8312b8b789. Normal commit hooks were not bypassed. Exactly one added test file, 65 lines; all changed paths satisfy the authorized test-only restriction.
Branch: codex/regression-tests, previous tip 2c5886eafcc0fbef70cf16dddc580c681dedac7c. Its production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a; no production history is merged.
Added file: frontend/src/screens/Approvals.request-isolation.test.tsx (two strict behavioral cases).
Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-topic-fixed/newsletter-reference-implementation, detached at the full source SHA above.
Publication worktree: /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation.

Invariant: ADR-141 section 4 / ADR-142 section 4: a selected option and optional feedback belong to the request being reviewed. Cache both details, choose index 1 and type a reason in request 7, then open request 8 via the persistent inbox. The second request must have no selected option, approval disabled, and an empty reason. Both new cases currently fail: index 1 is selected on request 8 and request 7's reason is retained. The approval-disabled assertion follows the failed radio assertion and is not reached. Associated with task-372, not task-315 through task-323; no accepted task was created or changed. No production fix, skip, xfail, or weakened assertion. The existing decision component also exhibits this on the tests branch's older base, so this is an existing cached-route defect made relevant by the new persistent split navigation, not claimed as introduced by ff2cbfb.

Exact commands and results (cwd is frontend in the validation worktree unless stated):
- node node_modules/vitest/vitest.mjs run src/screens/Approvals.request-isolation.test.tsx src/screens/Approvals.test.tsx: 19 existing tests passed, 2 new cases failed; exit 1.
- node node_modules/vitest/vitest.mjs run: 394 passed, 2 new cases failed; exit 1. Client coverage is not sufficient or green while these defects remain.
- node node_modules/typescript/bin/tsc -b: passed, exit 0.
- node node_modules/eslint/bin/eslint.js src/screens/Approvals.request-isolation.test.tsx: passed, exit 0.
- Publication worktree: node node_modules/vitest/vitest.mjs run src/screens/Approvals.request-isolation.test.tsx: same 2 strict failures, exit 1. This is application validation against the older branch base, separate from intended-source verification.
- Initial publication-worktree test invocation lacked node_modules (MODULE_NOT_FOUND, exit 1); rerun used a symlink to existing primary dependencies and reproduced both behavioral failures. No dependency installation was changed.
- Validation backend (cwd backend): PYTHON_DOTENV_DISABLED=1 ASSETS_DIR=/private/tmp/regression-66a9515-assets /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q: 2176 passed, 10 existing skips, 1 failed, exit 1, 171.23 seconds. Sole failure: tests/test_product_name.py::TestNoRetiredNameIsLeft::test_living_files_carry_no_retired_name, the already reported design-document consistency defect at docs/design/DESIGN.md:15 and :58 and docs/design/HANDOFF.md:32. Not an infrastructure failure; documentation was not edited.
- Contract check: exported app.openapi() to /private/tmp/regression-ff2cbfb-openapi.json using PYTHON_DOTENV_DISABLED=1 and DATABASE_URL derived by tests.checkout_database.test_database_url(), after the backend suite; exit 0. Then (cwd frontend) node node_modules/openapi-typescript/bin/cli.js /private/tmp/regression-ff2cbfb-openapi.json -o /private/tmp/regression-ff2cbfb-schema.d.ts; exit 0. diff -u src/api/schema.d.ts /private/tmp/regression-ff2cbfb-schema.d.ts: identical, exit 0. No generated output in the branch.

Earlier chronological checks in the same isolated worktree:
- 66a9515e63cb5a97b0cf140c652fb88e7494c474: backend pytest tests/test_demo_reset.py -q, with the same PYTHON_DOTENV_DISABLED and ASSETS_DIR environment: 13 passed, exit 0.
- 2d627e8aa4549afcf147fa3f7c48e7bc6f532aa9: same command: 14 passed, exit 0.
- 6ce82c5fed3a86eb1aa1b96666d783f8ba3eab50: backend pytest tests/test_block_set.py tests/test_click_attribution.py tests/test_duplication.py tests/test_hideable_fields.py tests/test_module_sourced_fields.py tests/test_read_models.py -q (same environment): 149 passed, exit 0; frontend node node_modules/vitest/vitest.mjs run src/screens/CampaignDetail.test.tsx src/screens/DeliveryAsSent.test.tsx: 10 passed, exit 0.
- 2d9a70813b49a95c266373126063fa8adaa37064: queue documentation only; no tests needed.
- aded12e9777df7fb42f820ded50abd30cb15e70d: complete client suite, 380 passed, exit 0. CSS rendering, contrast and responsive visual QA not performed.
- 08ac7399a99111e36955160c4f0986f557ce8eec: node node_modules/vitest/vitest.mjs run src/shell: 17 passed, exit 0.
Database safety: checkout-derived app_test_newsletter_reference_implementation_4a63fd; TEST_DATABASE_URL unset, dotenv disabled, no development database or .env read, mock providers and suite-wide real-provider refusal guard, explicit temporary asset root for the destructive demo reset. Backend suites ran serially.

Origin push: succeeded (exit 0): git push origin refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. git ls-remote --heads origin refs/heads/codex/regression-tests independently confirmed dcdade9c4f0f95ff1f9e1bb3761efe8312b8b789. The parent is the previous tests-branch tip above; no earlier batches or production history changed. Pending integration: this new batch only; do not land strict failures on main separately from their fix. Initial note creation hit EPERM on Backlog's metadata lock; authorized retry with repository metadata access succeeded. No tracking or memory files written.

Final assessment: chronological review through ff2cbfb19976e68ee21f0b3124f7f90781ff0a05 completed; previous cursor 5669a7ab13cc1ad64858ca52586088d0e4315e57 is its ancestor, no history rewrite. No new backend gaps identified in the demo or retirement cleanup. The approval regressions demonstrate missing cached-request isolation; coverage/suites are not green. No remaining infrastructure-blocked checks. Visual theme/contrast/responsive QA remains unverified. Strict changes are preserved in both isolated worktrees and published on origin, awaiting integration with a fix. Last primary HEAD check remained ff2cbfb19976e68ee21f0b3124f7f90781ff0a05.

Integration verification 2026-10-17: fea49faae970e2ebf4f66796c4835dfda1cb8651 integrates dcdade9 approval tests byte for byte and keys Decide by request id. In the isolated regression-approval-history worktree at that exact source, node node_modules/vitest/vitest.mjs run src/screens/Approvals.request-isolation.test.tsx src/screens/Approvals.test.tsx src/screens/CampaignDetail.test.tsx passed all 32 tests (exit 0), including both formerly failing strict regressions and the companion cached campaign-name test. Both approval regressions also pass in the complete client suites at 328e04d and f4de752. This batch is now integrated; later content/send state failures are separate, recorded in doc-34.
