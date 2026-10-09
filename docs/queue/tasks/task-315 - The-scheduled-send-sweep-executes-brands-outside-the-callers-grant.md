---
id: TASK-315
title: The scheduled-send sweep executes brands outside the caller's grant
status: To Do
assignee: []
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 08:23'
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
- [ ] #1 An integration granted sends.execute only in A cannot trigger or inspect a due send in B through process-due.
- [ ] #2 A person using A as working brand cannot sweep B; the intended scheduler path retains explicit authorization.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-1) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: process_due (backend/app/delivery/router.py:297) takes no working brand, and process_due_scheduled_sends (backend/app/delivery/service.py:598) fires every due send with that send's own brand_id.
<!-- SECTION:NOTES:END -->
