---
id: TASK-331
title: A held request still runs after its requester was switched off
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:12'
updated_date: '2026-10-10 19:38'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** An integration (or a person) can file a request that waits for a person's approval, for example a send. If the requester is deactivated, or loses the permission the action needs, before anyone decides, a later approval still runs the action. approve() in backend/app/approvals/service.py (around :292) claims and executes the held action; may_decide and requester_is_decider (:506-534) check only the approving person's current permission and the self-approval rule. The requester (requested_by_type, requested_by_id) is kept as history and never re-checked, and deactivating an integration or revoking a grant (backend/app/auth/integrations.py) does nothing to its open requests.

Why it matters: offboarding a misbehaving integration leaves its queued proposals approvable, and the approver cannot tell from the inbox.

Decided with the user 2026-10-09 ("void at decision"; recorded in the second 2026-10-09 addendum to ADR-142, written by the adr-author agent): when a person approves, the request is re-checked against its requester's standing at that moment. If the requester is no longer active or no longer holds the permission the held action requires, nothing runs; the request closes as withdrawn ("requester no longer allowed"), audited. The inbox marks such requests before a decision is made. One check at decision time covers both deactivation and grant revocation. A person who still wants the action does it under their own authority. Rejected: cancelling at switch-off time (needs hooks in every revocation path) and keeping today's behaviour.

Source: [[Interview Prep - Since 2026-09-18]] → Manager client, held approvals and machine reads, Q6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Approving a request whose requesting integration is deactivated runs nothing and closes it as withdrawn, audited
- [x] #2 Approving a request whose requester no longer holds the action's permission runs nothing and closes it as withdrawn, audited
- [x] #3 The approvals inbox shows that a pending request's requester is no longer allowed
- [x] #4 A request whose requester is still allowed approves and runs as before
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass, 2026-10-10. Three decisions taken by the user, recorded in the ADR-142 addendum by adr-author:
- declared request_permission on each action;
- a new 'withdrawn' status;
- one rule for every requester.

1. approvals/actions/base.py: ApprovableAction gains a required request_permission beside approve_permission. Declared values: send_fire sends.execute; content_ready content.manage (the policy of PUT /content/{content_id}/readiness/{channel}); ai_subject_apply ai.run. A test pins that each APPROVABLE_ROUTES action declares exactly required_permission() of its route.
2. approvals/db_models.py: WITHDRAWN = 'withdrawn' in STATUSES and DECIDED. The check constraint string gains it. scripts/migrate_0042_pending_action_withdrawn.sql drops and re-adds ck_pending_actions_status (0022's pattern). Applied to dev with scripts/migrate.py --apply before the .py edits run against it.
3. audit/service.py: APPROVAL_WITHDRAWN = 'approval.withdrawn' in the vocabulary.
4. approvals/service.py:
   - requester_allowed(db, row) returns True, False or None. It loads the requester (user or integration); system or unknown types give None, meaning no standing to lose. It calls has_permission with the request's brand when request_permission is brand-scoped, else ALL_BRANDS. An inactive principal holds nothing, so one call covers both deactivation and permission loss. A requester row that no longer exists counts as not allowed.
   - In approve(): after the expiry and action-exists checks and BEFORE the claim, a requester not allowed means a conditional transition pending to withdrawn (decided_at, decided_by the approver, decision_reason 'requester no longer allowed'), audited approval.withdrawn with the approver as actor, and an ActionResult refusal. Reject is unchanged.
5. approvals/router.py: PendingActionRow.requester_allowed (bool | None), computed for pending rows in list and detail.
6. Frontend: regenerate the API types. The Approvals list and ApprovalDetail show a notice on a pending request whose requester is no longer allowed ('approving will withdraw it, and nothing will run'). Status text 'withdrawn' shows as is.
7. Tests first.
   - Backend: an integration's held send, switched off, then approved, ends withdrawn with nothing sent and audited; the same with its grant revoked; the same for a deactivated person and for a person without ai.run; a still-allowed requester runs as before; the list shows requester_allowed; reject still works; the declaration test.
   - Frontend: the notice.
8. Mutation-check, full suites, Ruff, ESLint, tsc, commit, CI, live check on scratch data.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from writing the ADR-142 addendum ('Addendum 2026-10-09 (second)'), for the final-design pass:
(1) 'The permission the held action requires' has no source today. The action contract declares only approve_permission (backend/app/approvals/actions/base.py:43-53), and what the requester needed differs, e.g. ai.run to request an AI suggestion versus campaigns.manage to approve it. Nothing records it on the action or the row.
(2) Where 'withdrawn' is stored is open. It is not one of the six states in ck_pending_actions_status; a seventh means a migration and every status consumer (as executing did). It is also open whether it leaves pending by the same conditional transition as reject and expiry.
(3) Rotating a credential voids nothing: revoke_credential only sets revoked_at, and the integration and its grants stay. The addendum says so.

2026-10-10, built (commit 7ceb903). ADR-142, second 2026-10-09 addendum plus its 2026-10-10 paragraph (adr-author).

Final-design decisions by the user:
- request_permission is declared on each action and pinned to its route's policy by a test;
- a seventh status, 'withdrawn' (migration 0042, applied to dev);
- one rule for people and integrations.

Not a user decision: withdrawal uses the same conditional pending-to-withdrawn transition as reject and expiry. That is how every transition in the service works.

What changed:
- requester_allowed(db, row) in approvals/service.py returns True, False or None (None for system, unknown or unregistered). It uses has_permission, which returns nothing for an inactive principal, so one call covers deactivation and permission loss. The request's brand is used for brand-scoped permissions, else ALL_BRANDS; a grant on another brand does not count. A missing requester row counts as not allowed.
- approve() checks it after the expiry and action checks and BEFORE the claim. The request closes withdrawn (decided_by the approver, decision_reason 'requester is no longer allowed') and is audited approval.withdrawn. Reject is unchanged.
- PendingActionRow.requester_allowed is set on waiting rows in the list and the detail. React: the inbox's Requested-by cell and a role=status notice on the detail.

Existing tests that named fake requesters (integration #7 in test_approvals_ui.py) now use real integrations. test_channel_readiness approved after its machine() block had deleted the integration; it now approves inside it. Both are the new rule working as intended.

Tests:
- Backend: backend/tests/test_requester_standing.py, 10 tests. 6 failed first, reproducing the bug: a switched-off integration's send ran with 'Sent: 1 delivered'.
- Frontend: 3 tests in Approvals.test.tsx.

Mutations, each caught:
- allowed always: 6 failed;
- scope always all brands: 1;
- no audit: 4;
- wrong declaration: 1;
- inbox never says: 1;
- list notice removed: 1;
- detail notice removed: 1.

Suites:
- Backend 1634 passed, Ruff clean, schema check clean.
- Vitest 236, tsc, ESLint. One run hit a 5-second timeout in an untouched paging test under load; it took 237 ms with the change and 267 ms without, and two full reruns were green.

Live check: scratch integration 'task-331 scratch' (id 1953), switched off, with held request 1728 pointing at a send that does not exist.
- The inbox showed 'no longer allowed; approving withdraws it', and the detail showed the notice.
- The detail's Approve button is disabled for a request whose send does not exist (existing behaviour), so the server route was called directly as the signed-in person. It returned 'withdrawn: the requester is no longer allowed, so nothing ran'.
- The history shows withdrawn, decided by Initial admin, with the reason.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Approving a held request now re-checks its requester first. A person or integration that is switched off, or no longer holds the action's declared request permission, voids the request: nothing runs, and it closes as the new status 'withdrawn' (migration 0042), audited approval.withdrawn with the approver as actor. The inbox and the detail warn before anyone decides. Design decided with the user 2026-10-10: the permission is declared on each action, a seventh status, one rule for everyone (ADR-142 addenda). Verified by test_requester_standing.py (failed first, reproducing the bug), frontend tests, seven mutations caught, the full suites, green CI on 7ceb903, and a live check on a scratch request.
<!-- SECTION:FINAL_SUMMARY:END -->
