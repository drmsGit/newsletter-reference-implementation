---
id: TASK-206
title: 'A content-readiness approvable action, plus its APPROVABLE_ROUTES entry'
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-08 18:52'
labels:
  - backend
dependencies:
  - TASK-283
  - TASK-210
priority: p2
type: feature
ordinal: 200430
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **A content-readiness approvable action**, plus its `APPROVABLE_ROUTES` entry (Q6b). That table is fail-closed by omission, so without the entry a machine asserting readiness gets a hard 403 rather than a hold.

Source: [[Manager Workflow - design interview]] → What Cluster 2 produced, requirement 3 (Q2.6b).

**Verified against the code 2026-09-27:** `APPROVABLE_ROUTES` (`backend/app/auth/policy.py:262-264`) holds a single entry, `send.fire_send_instance`. `backend/app/approvals/actions/` holds only `send_fire.py` and `ai_subject_apply.py`.

Related: [[ADR-174 — Channel Readiness Is Asserted, Not Computed]].
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An integration's mark for a channel is held for a person: one request per record and channel, no deadline, the review showing the record, the channel and the readiness warning
- [x] #2 Approving marks the record ready in the approver's name; rejecting marks nothing; removing a mark stays direct
- [x] #3 A record of another brand holds nothing, and a retry answers with the same request
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-04: depends on task-282, the readiness state itself (split out of the task-274 design session).

2026-10-05 (task-282 design session):
- This now depends on task-283, the readiness state and routes, and on task-210: the readiness hold must carry no deadline (Manager Workflow Cluster 1, around line 358; ADR-142 addendum 2026-09-24).
- Until this task is built, task-283 refuses an integration's attempt to mark a record ready (nothing goes through unheld). An integration may still unmark directly; that is decided.
- Gap found 2026-10-05: an APPROVABLE_ROUTES entry alone will not hold a content.manage route. The guard raises ApprovalRequired only for SENDS_EXECUTE when the integration may not send unattended (backend/app/auth/dependencies.py, around 623-638), so it needs widening to the readiness route.
- The held payload carries path params only, so the channel must be a path parameter of the mark route.

Built 2026-10-08, commits 7db64ff and the wording fix after it. Already decided: Q2.6b and ADR-174 point 4 (held, a person decides; a person's own mark not held), ADR-174 addendum 2026-10-05 point 5 (unmark direct), ADR-142 addendum 2026-09-24 (no deadline, built by task-210).

Asked of the user 2026-10-08, one at a time, both with the recommendation:
1. One open request per record AND channel (not one per record, not one collecting channels): actions may declare a scope inside their subject.
2. The approver is recorded as the one who marked it; the integration stays in the request's history and audit.
Recorded in addenda of 2026-10-08 to ADR-174 and ADR-142 (adr-author), and a playbook entry.

Where it landed:
- backend/app/approvals/actions/content_ready.py: content.mark_ready (approve_permission content.manage, default_ttl_seconds None, requester_may_decide False, subject content, scope the path's channel; subject_in_brand, summarise, describe with rows and the readiness warning, execute marking in the approver's name).
- backend/app/auth/policy.py: the route in APPROVABLE_ROUTES and a new HELD_FOR_EVERY_INTEGRATION set by method (PUT only); backend/app/auth/dependencies.py holds on either rule.
- pending_actions.subject_scope (migration 0040, empty not NULL so the index still holds for unscoped actions), in the one-open-request index, in request_approval (a scoped action given no scope is refused, not held under the empty one - raised by the adr-author), in main.py's handler and its retry lookup.
- approve() passes approver= to an action whose execute declares it (inspect.signature), so the existing actions keep their signatures.
- backend/app/content/router.py: the integration branch is now a defensive refusal behind the guard.

Found and fixed on the way:
- The action registry reloaded its own base and registry modules mid-scan, so a new declaration type came back and an action file named between them (content_ready.py) was skipped with no warning; they are skipped now, pinned by test_an_action_named_between_base_and_registry_is_discovered.
- The 202 held reply said the send is held for every held request; it now names the action (found in the live check).

Tests: test_channel_readiness.py +7 (held not applied, one per channel and the retry, the review, approve marks with the approver, reject, foreign brand, missing scope refused); test_approvals.py +1 (the registry). 12 mutants, all killed. Backend 1483, client 224, schema check and types clean.

Live check 2026-10-08, scratch record zz-scratch task-206 and a scratch integration (both removed): the integration's mark for push answered 202 with no deadline; the React approval detail showed the record, Push, status, not yet marked, No deadline and the warning under Before you decide; Approve and run marked it; the record page read Marked ready by ds@diede-slembrouck.de; the audit trail read requested by the integration, granted and ready_marked by the user with the request's id.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An integration that says a record is ready for a channel no longer gets a 403: its mark is held in the approval inbox for a person, one request per record and channel, with no deadline; the reviewer sees the record, the channel and the readiness warning, and approving marks it ready in the approver's name. Decided with the user and recorded in 2026-10-08 addenda to ADR-174 and ADR-142. Two defects found on the way were fixed: the action registry silently skipped some action files, and the held reply always talked about sending. Verified by 8 tests (12 mutants killed), the full suites and a live approval on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
