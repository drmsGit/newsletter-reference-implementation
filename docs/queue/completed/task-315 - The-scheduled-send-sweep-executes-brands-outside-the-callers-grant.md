---
id: TASK-315
title: The scheduled-send sweep executes brands outside the caller's grant
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 08:33'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. A credential restricted to brand A can cause mail to be sent for brand B. Reachable today through POST /delivery/process-due (and the frozen UI's equivalent).

Evidence: backend/app/delivery/router.py:297-315 calls process_due_scheduled_sends without an actor or working-brand argument. backend/app/delivery/service.py:598-629 selects every due scheduled send and invokes each with that row's own brand_id. The request guard checks sends.execute in the declared working brand; passing the target row's brand to the service is not authorization for it.

Reproduction: give an integration sends.execute only in A and unattended-send permission; schedule a due mock send in B; call process-due with A as working brand. The B send is fired and its ID returned. This behavior was reproduced in the first review stage using the disposable test database and mock provider.

ADR-166's authenticated principal and ADR-172's explicit brand scope require authorization against the rows affected. Keep the internal scheduler seam if needed, but constrain the request-driven sweep to authorized brands and apply the appropriate execution policy to each.

Related: task-16 and task-38 fixed default-union scope, but this explicit cross-brand sweep remains a distinct escape.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An integration granted sends.execute only in A cannot trigger or inspect a due send in B through process-due.
- [x] #2 A person using A as working brand cannot sweep B; the intended scheduler path retains explicit authorization.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-1) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: process_due (backend/app/delivery/router.py:297) takes no working brand, and process_due_scheduled_sends (backend/app/delivery/service.py:598) fires every due send with that send's own brand_id.

2026-10-09: fixed (commit 28aa4e8; CI green, run 37905332941).

Design choice, made without a separate question because ADR-172 already decides it: the working brand is resolved once and carried into every query. The sweep fires only the working brand's due sends, and a deployment with several brands calls it once per brand, declaring each with X-Brand. The rejected alternative was sweeping every brand where the caller holds sends.execute. It is more convenient for a scheduler, but it would be the one route that spans brands from a single call. If a single cross-brand scheduler call is ever needed, that is a new decision, not this fix.

The unattended-send rule needed no change. An integration without may_send_unattended is already refused on process-due: ApprovalRequired with no approvable action (backend/app/auth/dependencies.py:634-650).

Change:
- process_due_scheduled_sends(db, *, brand_id) filters SendInstanceDB.brand_id (backend/app/delivery/service.py). Its old comment, "a scheduler has no working brand", was wrong: a machine always declares one (ADR-166 point 8).
- POST /delivery/process-due passes Depends(working_brand) (backend/app/delivery/router.py).
- The frozen Jinja button /ui/deliveries/process-due passes working_brand_id(request, db) (backend/app/frontend/router.py).
- schema.d.ts was regenerated (description only).

Tests: backend/tests/test_process_due_brand.py covers four cases:
- the service fires only the given brand's due sends;
- the brand is required (TypeError);
- the review's reproduction through the route: an integration with sends.execute and unattended sending in A fires A's send and not B's;
- the Jinja button, as a signed-in person.
The sweep's sends are recorded by monkeypatching send_send_instance, so nothing renders or sends. Mutation check: 4 of 4 caught (brand filter dropped, brand optional, API route ignoring the brand, Jinja route ignoring the brand). Full suite: 1539 passed.

No live check. The dev data has no scheduled send at all (checked), so a live call could only return an empty list, which the route test already proves.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The scheduled-send sweep now fires only the working brand's due sends, through the JSON route and the frozen Jinja button. A credential for brand A can no longer fire brand B's mail, and a multi-brand scheduler calls once per brand (ADR-172). Verified by test_process_due_brand.py (the review's reproduction among 4 tests, 4/4 mutants caught), the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
