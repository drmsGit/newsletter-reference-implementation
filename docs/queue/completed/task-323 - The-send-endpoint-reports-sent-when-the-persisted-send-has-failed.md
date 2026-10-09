---
id: TASK-323
title: The send endpoint reports sent when the persisted send has failed
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 09:03'
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
- [x] #1 The send endpoint returns the actual persisted outcome for failed and partial_failed batches.
- [x] #2 A no_recipients result is not reported as sent.
- [x] #3 Response documentation and client behavior agree with the returned send outcomes.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-6) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: the send route returns a hard-coded status sent (backend/app/delivery/router.py:251-253) and ignores the persisted parent status.

2026-10-09: fixed (commit 9bbf2f8; CI green on 72df52b).

Change:
- send_send_instance (backend/app/delivery/service.py) returns the persisted outcome: sent, partial_failed, failed or no_recipients. The parent-status derivation that sets it is unchanged (task-98).
- POST /delivery/send-instances/{id}/send (backend/app/delivery/router.py) returns {"status": <outcome>}. Its 200 documentation names the four values and says a completed run is not a successful delivery. schema.d.ts was regenerated, and tsc passes.
- The held-send approval (backend/app/approvals/actions/send_fire.py) leads its message with the outcome, for example "Failed: 0 delivered, 1 failed, 0 excluded.", instead of "Sent:". ok=True is kept: the action ran. Whether an all-failed send should count as an approval execution failure in the audit is a different question, left as it is.
- The frozen Jinja send button already redirects to the send's detail page, which shows the stored status.
- No React screen calls this route yet. The send screen is task-67.

Tests (backend/tests/test_send_outcome.py), through the route as a machine with sends.execute and unattended sending:
- every delivery rejected gives "failed";
- one of two rejected gives "partial_failed";
- no recipients gives "no_recipients";
- a success gives "sent";
- the approval message for a failed send starts "Failed:".
The first three failed before the fix, all answered "sent". Mutation check: 2 of 2 caught (route hard-coding "sent"; message assuming "Sent"). Full suite: 1561 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The send endpoint now returns the send's persisted outcome (sent, partial_failed, failed or no_recipients) instead of an assumed sent; its documentation names the four, and the held-send approval message leads with the outcome. Verified by 5 tests (3 answered sent before the fix), 2/2 mutants caught, the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
