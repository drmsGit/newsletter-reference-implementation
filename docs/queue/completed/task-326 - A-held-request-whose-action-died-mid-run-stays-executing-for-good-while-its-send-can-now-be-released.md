---
id: TASK-326
title: >-
  A held request whose action died mid-run stays 'executing' for good, while its
  send can now be released
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 14:17'
updated_date: '2026-10-09 14:26'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300195
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Decision: a held request whose approved action died mid-run stays "executing" for good, and since ADR-192 its send can be released but the request cannot.** Found 2026-10-09 by the adr-author while writing ADR-192 (task-325). Filed at the user's request.

**What happens.** Approving a held action moves the request from pending to executing (backend/app/approvals/service.py:307), runs the action, and then moves it to approved or failed (:345-367). If the PROCESS dies while the action runs, for example send_fire delivering a send, the request stays "executing". The open-request index ux_pending_actions_one_open_per_subject (backend/app/approvals/db_models.py:160-166) counts both "pending" and "executing" as open. So no new held request can be raised for that subject (that send) until the row is cleared, which today means SQL.

**This is deliberate today.** [[ADR-142 — Autonomous Workflows and the Automation Boundary]], addendum 2026-09-29, point 6: "A crash during execution leaves the row executing, deliberately, and nothing retries it". Nobody can know whether the action ran, and re-approving would be the double execution that addendum closes; "resolving it is a person's investigation, not a button". It names this "the same shape as a send left in sending".

**What changed.** [[ADR-192 — A Stranded Send Is Flagged, and a Person Releases It]] (task-325) gave the send that shape's answer. A send stranded in "sending" is flagged after 30 minutes without activity, and a person releases it to "failed", safely, because task-318 makes a retry skip what may have been sent. Now the two halves disagree:
- a stranded send can be released and retried by a person directly;
- its held request stays "executing", blocking a machine from asking again for that send.
Releasing the send does not touch the request.

**What has to be decided:**
1. **Keep point 6 as it is.** The stuck request stays a matter for investigation; a person retries the send directly, and a machine cannot re-request it until someone clears the row by hand. Cheapest, but it keeps a SQL-only path.
2. **The same answer as ADR-192, for requests.** Flag a request "executing" for longer than a threshold, and let a person mark it failed (people only, audited). Whether a retry is then safe depends on the action, which is the point 6 reasoning: for send_fire it is, through task-318; other actions (content readiness, applying an AI suggestion) would need checking one by one.
3. **Couple them.** Releasing a stranded send also fails its executing held request, since the send's own release already establishes that the run died.
Any of these amends ADR-142 point 6 through a dated addendum (adr-author), not a rewrite.

**Related:** task-325 and ADR-192 (the send half), task-318 (retry rules), task-124 part (c).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: option 3 decided by the user and built (commit 05088de; CI green). Recorded as a 2026-10-09 addendum to ADR-142, amending its first 2026-09-29 addendum's point 6 for send_fire only, and a note on ADR-192.

Change:
- backend/app/approvals/service.py: fail_stuck_requests(db, action_key, subject_type, subject_id, reason) moves the matching "executing" request(s) to "failed" with execution_error = reason, under a row lock and WITHOUT committing, and returns their ids.
- backend/app/delivery/service.py: release_send_instance calls it for send.fire_send_instance on this send, after the stranded check and before its single commit, so the send and its request change in one transaction. It now returns (counts, failed request ids).
- backend/app/delivery/router.py: the send.released audit entry lists held_requests_failed, and each failed request gets an approval.failed entry by the releasing person. The audit entries are written after that commit, through record_from_request.
- Unchanged by decision: requests for other actions or other sends, requests still "pending", and every other action's crashed request (ADR-142 point 6 still applies; retry safety has not been checked action by action).

Tests (backend/tests/test_stranded_send.py, class TestTheHeldRequest):
- releasing fails the stuck request with its reason, audits approval.failed by the person, and frees the subject for a new pending request;
- requests for another send or another action stay "executing";
- a refused release (send not stranded) leaves the request alone.
The first failed before the fix. Mutation check: 5 of 5 caught (request not failed; any action's request failed; any send's request failed; not audited; a refused release still failing the request). Full suite: 1595 passed.

Live check, on scratch data: scratch send 6 ("SCRATCH task-326 stranded + held") was left "sending" two hours idle, with held request 1727 "executing". POST /release as the signed-in person returned 200 and status "failed". Request 1727 is now "failed" with the reason "released with its stranded send (ADR-192)…", the audit has approval.failed by the user, and the send.released entry lists held_requests_failed [1727].
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Releasing a stranded send now also fails the held request whose approval was running it, in the same transaction and audited by the releasing person, so a new request for that send can be raised without SQL. Other actions' crashed requests keep ADR-142's investigate-by-hand rule. Decided as option 3 (ADR-142 addendum 2026-10-09). Verified by 3 tests (5/5 mutants caught), the full suite, CI green and a live check on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
