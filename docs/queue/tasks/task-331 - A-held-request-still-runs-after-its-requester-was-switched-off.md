---
id: TASK-331
title: A held request still runs after its requester was switched off
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 18:12'
updated_date: '2026-10-10 19:19'
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
- [ ] #1 Approving a request whose requesting integration is deactivated runs nothing and closes it as withdrawn, audited
- [ ] #2 Approving a request whose requester no longer holds the action's permission runs nothing and closes it as withdrawn, audited
- [ ] #3 The approvals inbox shows that a pending request's requester is no longer allowed
- [ ] #4 A request whose requester is still allowed approves and runs as before
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
<!-- SECTION:NOTES:END -->
