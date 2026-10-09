---
id: TASK-331
title: A held request still runs after its requester was switched off
status: To Do
assignee: []
created_date: '2026-10-09 18:12'
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
