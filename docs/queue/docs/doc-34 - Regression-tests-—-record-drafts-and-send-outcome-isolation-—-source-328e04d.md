---
id: doc-34
title: Regression tests — record drafts and send outcome isolation — source 328e04d
type: other
created_date: '2026-10-17 13:03'
updated_date: '2026-10-17 13:58'
---
Source covered: 328e04d7d31855f092a591875e616112c15f970a (task-372). The content cases were first validated at d47bb8fb55876f3ae78143ed5b8eb71ffc7c1870; the send case at 1c24eca4872404f3bbbac766c54550f5bc4ce576; all three were then validated together against the exact source above.
Tests-branch batch commit: dec60cf3831ad2202206d8bcdf48be678b597047. Parent dcdade9c4f0f95ff1f9e1bb3761efe8312b8b789. Exactly the two authorized test paths changed (134 added lines); byte-identical to the validated copies. Normal hooks were not bypassed.
Previous tests-branch tip: dcdade9c4f0f95ff1f9e1bb3761efe8312b8b789. Branch codex/regression-tests retains production base 28aa4e88f4846768a18fd81b66949f959cd3b38a. No production changes are merged into it.
Added files: frontend/src/screens/ContentDetail.record-isolation.test.tsx (2 cases), frontend/src/screens/SendVariant.send-isolation.test.tsx (1 case).
Validation worktree: /Users/diedeslembrouck/.codex/worktrees/regression-approval-history/newsletter-reference-implementation, reused clean, pinned sequentially to each exact source. The files remain preserved there.
Publication worktree: /Users/diedeslembrouck/.codex/worktrees/regression-315/newsletter-reference-implementation; identical test files copied, no production edits.

Strict defects, all associated with task-372 (no new accepted tasks created or edited):
1. A headline whose save failed on record 42 appears as the draft on cached record 77 when both stored headlines are identical. ADR-180: edit/refusal state belongs to the edited record. The expected stored headline assertion fails; the following blur/no-cross-record-write assertions are not reached and remain unverified.
2. The AI source typed for record 42 remains in the source field of cached record 77. ADR-141: a record-level brief stays with its target.
3. After firing send 9 through a mocked endpoint, continuing cached draft send 10 from the planned list still displays Sent. from send 9. ADR-183 governs the send flow and per-send outcome. The no-false-Sent assertion fails; actually firing send 10 after this assertion is not reached and remains unverified.
These are state-isolation defects, not API fixes. Task-323 is completed: it fixed the backend endpoint returning a hard-coded sent status. This new cross-send client-state failure is related in principle but is not a claim that task-323 remains open. No failing assertion was weakened, skipped, or marked expected-to-fail. Production fixes are outside this watcher scope.

Verification, actual exit codes (all cwd frontend in the validation worktree unless stated):
- At d47bb8fb55876f3ae78143ed5b8eb71ffc7c1870: node node_modules/vitest/vitest.mjs run src/screens/ContentDetail.record-isolation.test.tsx: 2 strict failures, exit 1, displaying Spring-only draft and the prior AI brief on the winter record.
- At 1c24eca4872404f3bbbac766c54550f5bc4ce576: node node_modules/vitest/vitest.mjs run src/screens/SendVariant.send-isolation.test.tsx: 1 strict failure, exit 1, showing Sent. while the delivery link points at /deliveries/10 and only send 9 was fired.
- At 328e04d7d31855f092a591875e616112c15f970a: node node_modules/vitest/vitest.mjs run: 406 passed, exactly the 3 new cases failed; exit 1. No other client failures.
- At that same source: node node_modules/typescript/bin/tsc -b: exit 0.
- At that same source: node node_modules/eslint/bin/eslint.js src/screens/ContentDetail.record-isolation.test.tsx src/screens/SendVariant.send-isolation.test.tsx: exit 0.
- Additional verification at f4de7521be6bac334518f168f5a27abd1586af00 after later audience/recipient changes: node node_modules/vitest/vitest.mjs run: 409 passed, the same 3 new cases failed; exit 1. node node_modules/typescript/bin/tsc -b: exit 0. This does not replace the exact intended-source validation above.
- Publication worktree (older production base): node node_modules/vitest/vitest.mjs run src/screens/ContentDetail.record-isolation.test.tsx src/screens/SendVariant.send-isolation.test.tsx: exit 1. The refused-headline case reproduces the behavioral failure. The AI-brief case cannot reach its assertion because that base has no Source UI. The send suite cannot collect because that base has no SendVariant.tsx. These are application/compatibility blockers on the older base, separate from the three verified defects at the intended source. Resolving them requires newer production code, prohibited on this branch; tests were preserved unchanged instead of introducing skips or copying production files. No passing tests-branch suite is claimed.

Safety/limitations: no backend or schema changes in the reviewed range, so no backend tests or DB operations were needed. All new test HTTP calls are intercepted by local handlers with mock providers; no .env reads, real mail or model calls. Existing dependencies are referenced read-only; no shared installation changes. No contract changes in this range. The previous backend retired-name guard failure is not rechecked or claimed fixed. Visual theme/contrast/responsive QA remains unverified. Coverage is not sufficient/green while the 3 strict behavioral failures remain.
Origin push: succeeded, exit 0: git push origin refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. Independently confirmed by git ls-remote --heads origin refs/heads/codex/regression-tests: dec60cf3831ad2202206d8bcdf48be678b597047. All prior batches and the old production base remain unchanged. No main or PR action. This new batch awaits integration with its fixes; compatibility blockers on the older base remain as recorded above.

Further source validation after the monitoring/history layout commit: at 4346fcca5806e125567ebc062a3251797c85f5a2 in the same isolated worktree, node node_modules/vitest/vitest.mjs run returned 409 passed, the same 3 strict new failures, exit 1; node node_modules/typescript/bin/tsc -b passed, exit 0. No new failure from the extracted status chip or wide tables. The later 0a1ae32b53dd32c0649aceaaa964be3d1fa02030 changes queue notes only.

Integration verification 2026-10-17: b57a86a347d103621c7b502f99282906fe0f4acb integrates both files from dec60cf byte for byte (blobs 4a1b3b65a057182b2cbccf162d3927371b09c7b6 and 58793603893ffad44fb551c51b816437081bf3d7), keys the record page by record id and generation and the send step by send id. In the isolated regression-envelope worktree at that exact commit, node node_modules/vitest/vitest.mjs run src/screens/ContentDetail.record-isolation.test.tsx src/screens/SendVariant.send-isolation.test.tsx passed all 3 tests, exit 0. The full client suite at 8973758 passed all 419 tests, exit 0. No strict failures remain from this batch; its integration is complete.
