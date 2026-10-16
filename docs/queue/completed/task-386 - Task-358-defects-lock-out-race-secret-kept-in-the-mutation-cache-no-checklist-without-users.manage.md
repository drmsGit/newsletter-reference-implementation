---
id: TASK-386
title: >-
  Task-358 defects: lock-out race, secret kept in the mutation cache, no
  checklist without users.manage
status: Done
assignee:
  - '@claude'
created_date: '2026-10-16 17:39'
updated_date: '2026-10-16 17:48'
labels:
  - backend
  - frontend
dependencies: []
type: bug
ordinal: 100400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Three defects in task-358's administration work (commits bd584eb, ad9bf29, 79f3a7a), found by Codex's regression batch (tests-branch commits 1c74596 and 836cad5; pre-stage notes doc-28 and doc-29, read 2026-10-17). Each has a failing test there that lands with its fix.

1. **Lock-out guard race.** `set_active`, `revoke_assignment` and `set_role_permissions` (`backend/app/auth/service.py`) check "would anybody still hold users.manage?" and then write, each in its own transaction. Two overlapping removals of the last two managers both see the other still there, both pass, and nobody is left (ADR-150 addendum 2026-10-16, point 1). Test: `backend/tests/test_admin_lockout_concurrency.py` (three cases: deactivate, revoke, permissions).
2. **An issued key's secret stays in the client's mutation cache.** `useIssueKey` (`frontend/src/api/resources.ts`) returns the whole KeyIssued response from its mutation function, so TanStack Query keeps `secret_key` in the mutation's state after the dialog closes. ADR-166's addendum of 2026-10-16 says it is never in the client's caches. Test: `frontend/src/screens/IntegrationDetail.secret.test.tsx`.
3. **A person with integrations.manage but not users.manage gets no grant checklist.** The integration page reads the permission catalogue and the brands from `/auth/permissions` and `/auth/brands`, which need users.manage (they must stay so). Test: `frontend/src/screens/IntegrationDetail.permissions.test.tsx`, plus a backend case in `test_admin_lockout_concurrency.py` that the admin routes stay closed to them.

Fix direction: serialise the guarded writes (a transaction-level advisory lock, so the check and the write cannot interleave); keep the secret out of the mutation's result; give the integration page its catalogue from the integrations API and its brands from the session (a person can only grant on brands they hold).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Overlapping removals of the last two managers leave one
- [x] #2 No client cache holds an issued secret after its dialog closes
- [x] #3 A person with integrations.manage alone can tick an integration's grants
- [x] #4 Codex's three test files are on main and pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed 2026-10-17 (commit 8d81526), CI green. 1: _lock_access (pg_advisory_xact_lock, one key) at the start of each guarded write in backend/app/auth/service.py, held to commit; Codex's three concurrency cases pass. 2: useIssueKey(id, onSecret) hands the secret to the dialog and returns only the credential. 3: GET /integrations/permissions (integrations.manage) and the session's brands feed the checklist; /auth/permissions and /auth/brands stay users.manage. Codex's permissions and secret tests adapted to the new sources (headers say so), rules unchanged; test_auth.py gets Codex's extra admin; Codex's content-figures delivery-scope test brought in too. Mutations: no lock, secret as the result, catalogue from users admin — all caught. pytest 2105, vitest 344.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The lock-out guard takes turns (advisory lock), so overlapping removals cannot leave nobody able to manage users; an issued key's secret never enters a client cache; integration grants work with integrations.manage alone. Codex's failing tests landed with the fixes. Verified by mutation checks, pytest 2105, vitest 344 and CI on 8d81526.
<!-- SECTION:FINAL_SUMMARY:END -->
