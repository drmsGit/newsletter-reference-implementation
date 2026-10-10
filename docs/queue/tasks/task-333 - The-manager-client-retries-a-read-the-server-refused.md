---
id: TASK-333
title: The manager client retries a read the server refused
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 18:12'
updated_date: '2026-10-10 20:01'
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
- [ ] #1 A query that gets a 4xx response is not retried
- [ ] #2 A network failure or 5xx response is still retried once
- [ ] #3 The rule is explained at the QueryClient defaults
<!-- AC:END -->
