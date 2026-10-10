---
id: TASK-333
title: The manager client retries a read the server refused
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:12'
updated_date: '2026-10-10 20:07'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Every query in the manager client retries once on any thrown error: frontend/src/main.tsx:18-27 sets retry: 1 globally, with no comment, from the scaffold commit f9d3c13. frontend/src/api/resources.ts:66-75 turns every non-OK response into an HttpError carrying its status, and nothing filters by status. Only the session read opts out (frontend/src/api/session.ts:99-107), because a 401 there means signed out.

So a 403 (not allowed), 404, 409 or 422 is requested twice. Repeating it cannot change the answer, the error is shown later than necessary, and anyone reading logs or the audit trail sees doubled denials. Nothing on record (ADR-173, docs/implementation/TanStackQuery.md, tasks, decision log) ever chose this.

Decided in the 2026-10-09 interview review (Client Q1): retry only network failures and 5xx responses, never 4xx. The predicate reads HttpError.status. Write the rule as a comment at main.tsx.

Source: [[Interview Prep - Since 2026-09-18]] → Manager client, held approvals and machine reads, Q1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A query that gets a 4xx response is not retried
- [x] #2 A network failure or 5xx response is still retried once
- [x] #3 The rule is explained at the QueryClient defaults
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit d27b09f). The query client's defaults moved to frontend/src/api/queryClient.ts (createQueryClient), used by main.tsx. retryOnceUnlessAnswered retries once only for a network failure or a 5xx, never a 4xx. The session read keeps its own retry: false.

Tests: frontend/src/api/queryClient.test.ts, 12 tests. With the old retry: 1, 7 failed: every refused status was retried, and a 403 was fetched twice.

Mutations, each caught:
- 4xx retried again: 7 failed;
- the client back on retry: 1: 1 failed.

Checks: vitest 248, tsc, ESLint, CI green.

Live check: opening /manager/approvals/987654321 made one GET /approvals/987654321, which returned 404 and was not repeated.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A read the server refused is no longer asked twice: the manager client retries once only on a network failure or a server error (5xx), never on 401, 403, 404, 409, 422 or any other 4xx. The rule lives in the new frontend/src/api/queryClient.ts with its reason. Verified by queryClient.test.ts (failed first under the old setting, two mutations caught), the full frontend checks, green CI on d27b09f, and a live 404 that was fetched once.
<!-- SECTION:FINAL_SUMMARY:END -->
