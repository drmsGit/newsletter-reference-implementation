---
type: adr
status: accepted
topic:
  - architecture
  - api
  - frontend
created: 2026-10-03
modified: 2026-10-03
source:
  - "task-88 (one standardized pagination mechanism across every data-heavy list endpoint)"
  - "[[Manager Workflow - design interview]] Cluster 3 gap 10 and Cluster 2 requirement 5"
  - "Decided by the user 2026-10-03"
depends_on:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]"
  - "[[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]"
  - "[[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]]"
  - "[[ADR-184 — API Documentation Exposure Is a Deployment Setting]]"
---

## Status
Accepted

## Context

[[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] point 7 made server-side pagination a precondition rather than an optimisation: a reference architecture is copied by adopters of very different sizes, so the API must not assume a record count. It said *that* the API pages. It did not say *how*, and nothing since has.

**The JSON plane has 36 GET routes that return lists, and two of them page (verified 2026-10-03).** `GET /approvals/` and `GET /delivery/send-instances` accept `limit` (default 50, maximum 200) and `offset` query parameters and return a plain list with no total. Both were added on 2026-10-02 and 2026-10-03 as a stopgap that explicitly deferred the shape to this task. Every other list route ends in `.all()` and returns everything it finds. The worst one the Manager Workflow design interview named (Cluster 3 gap 10) is `GET /campaigns/decision-slots/{id}/resolutions`, which reads the table its own model comment calls the fastest-growing in the schema.

**A page without a total cannot say where it is.** The stopgap routes return a page and nothing else. A client cannot render "page 2 of 7", and the only way it can decide whether to offer "older" is to assume more exist whenever a page comes back full. When the size of the set divides exactly by the page size, the last click lands on an empty page.

**The contract is the generated schema, so anything outside it does not exist for the client.** [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 makes the manager's API client generated from `/openapi.json` and never hand-written; the result is `frontend/src/api/schema.d.ts`. A total carried in a response header would be invisible to that typed client. [[ADR-184 — API Documentation Exposure Is a Deployment Setting]] treats the same schema as the route inventory of the plane.

**Changing the shape is cheapest now.** No external client depends on the API before public beta. A breaking change to a response shape costs the React client and the tests in this repository, and nothing else.

**Filtering is related but separate.** Cluster 2 requirement 5 of the same interview asks for server-side filtering on content, campaigns, audiences, recipients and approvals, and [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] point 7 pairs the two. This record decides the paging and the one rule filtering must obey with it; it does not decide the filters.

## Decision

**1. A list whose length grows with use of the system is paged. A list whose length is fixed by code or configuration stays a plain array.**
Records created by people, recipients, providers or machines grow with use, and their lists are paged. Categories, field definitions, module types, decision strategies and one variant's modules are fixed by code or configuration, and their lists are returned whole as a plain array. The test is "does this grow with use", not "is it long today".

**2. A paged endpoint returns one envelope: `{items, total, limit, offset}`.**
`total` is the size of the whole filtered set, counted with the same filters as `items`. The total travels in the response body, not in a header, so it is part of the typed contract.

**3. There is one shared mechanism.**
A single query-parameter dependency provides `limit` (default 50, maximum 200, minimum 1) and `offset` (0 or more), and one generic response model provides the envelope. No route defines its own paging parameters or its own paged shape.

**4. Every paged route has a stable, declared order with `id` as the final tie-breaker.**
Pages neither overlap nor skip. The order is newest first unless the route states a reason for another; the decision history, for example, orders by when a request ended.

**5. Paging is offset and limit, not cursors.**
At this project's realistic scale offset paging is sufficient: the deployment send cap is in the hundreds, and catalogues and recipient bases are in the low thousands per brand. A cursor scheme would be complexity without a user.

**6. Filtering is route-specific query parameters alongside the paging dependency, and is not decided here.**
Cluster 2 requirement 5 remains its own work. One rule binds it now: a filter applies identically to `items` and `total`.

**7. Applying this is a breaking change to each adopted route's response shape, accepted now.**
Nothing outside this repository consumes the API yet. The React client and the tests change with each route.

## Consequences

### Positive

- **One shape to learn.** Every paged route answers in the same envelope with the same parameters, so a client, a test or an integrator learns it once.
- **"Page N of M" and an exact last page become possible.** With `total` in the body, a client knows when it has reached the end instead of guessing from a full page, and the empty last page disappears.
- **The worst unbounded reads stop loading everything.** `GET /campaigns/decision-slots/{id}/resolutions` and the other routes on the build list stop returning whole tables.
- **The contract shows the total.** Because it is in the body and not a header, `frontend/src/api/schema.d.ts` types it like any other field, as [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 requires.

### Negative

- **Every adopted route breaks its response shape.** Clients that read a list must read `.items` instead. That is accepted under point 7, but each adoption touches the client and the tests.
- **Each page costs a count query.** `total` needs a second query per request. It is acceptable at this scale, and it shares the filtered query with `items`, but it is an extra round trip on every page.
- **Two kinds of list response now exist.** A route returns either the paged envelope or a plain array, and an author must choose between them by point 1's test. A wrong call is a breaking change to correct later.
- **Offset paging can shift under concurrent inserts.** If rows are added between two requests, an item can appear on two consecutive pages. Accepted at this scale under point 5.

## Notes

- **Not a supersession, and not an addendum.** [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] point 7 decided that list routes page server-side; this record decides the mechanism and the shape, which that record left open. **One wording tension should be stated rather than passed over:** point 7 there says *every* list route pages, while point 1 here keeps code- and configuration-fixed lists as plain arrays. Point 7's stated reason is that the product must not assume a *record count*, and a list fixed by code has no record count to assume, so the two are read here as consistent. Whether ADR-175 should carry a dated addendum saying so is not decided here.
- **Which routes adopt this is a build list, not part of the decision.** As of 2026-10-03 the lists that grow with use are: recipients; content records; campaigns; audience groups, and one group's members; a decision slot's resolutions; a send's executions; an execution's events; overrides; provider quarantine; the consent sync log; consent drift; approvals; deliveries; decision slots; and campaign monitoring. Two are borderline and are judged by point 1 at build time: the content versions of one record, and one campaign's variants.
- **The two stopgap routes already match.** `GET /approvals/` and `GET /delivery/send-instances` use the parameter names and limits chosen in point 3, so their callers change only in reading `.items` and gaining `total`.
- **Paged queries stay brand-scoped.** [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]] still governs every query behind a paged route, and `total` counts only within the working brand, as `items` does.
- **Not decided here:** the filter parameters for any route (point 6, Cluster 2 requirement 5); the order of any individual route beyond the newest-first default and the `id` tie-breaker; and the borderline routes named above.
- **The decision log has no entry for this decision.** `docs/playbook-strategy.md` records the unpaginated resolutions route and the mandatory server-side pagination in its Manager Workflow interview entry, but the shape decided on 2026-10-03 in task-88 is recorded only in the queue and here.

## Related ADRs

### Depends On
- [[ADR-002 — API First Architecture]]
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]
- [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]]
- [[ADR-184 — API Documentation Exposure Is a Deployment Setting]]
