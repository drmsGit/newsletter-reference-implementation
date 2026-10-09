---
id: TASK-323
title: The send endpoint reports sent when the persisted send has failed
status: To Do
assignee: []
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 08:23'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: medium. Operators and API clients receive a successful-send claim for unsuccessful delivery. Reachable today.

Evidence: backend/app/delivery/router.py:242-252 invokes the service then returns a hard-coded status of sent. backend/app/delivery/service.py:1143-1172 correctly derives sent, partial_failed, failed or no_recipients from child outcomes.

Reproduction: make every mock provider result success=False and call the send endpoint. The persisted parent is failed but the HTTP response is 200 with status sent. Reproduced in the first review stage. A normal return from the service does not imply successful delivery.

The brief explicitly prioritizes errors reported as success. Return the persisted outcome and make the response contract distinguish completion of execution from successful delivery.

Related: completed task-98 repaired parent-state truthfulness; the route still discards that truth. The send-fire approval action also warrants checking for the same assumption when the maintainer implements this fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The send endpoint returns the actual persisted outcome for failed and partial_failed batches.
- [ ] #2 A no_recipients result is not reported as sent.
- [ ] #3 Response documentation and client behavior agree with the returned send outcomes.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-6) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: the send route returns a hard-coded status sent (backend/app/delivery/router.py:251-253) and ignores the persisted parent status.
<!-- SECTION:NOTES:END -->
