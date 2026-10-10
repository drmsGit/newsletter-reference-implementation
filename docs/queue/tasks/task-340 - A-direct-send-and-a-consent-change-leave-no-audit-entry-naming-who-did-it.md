---
id: TASK-340
title: A direct send and a consent change leave no audit entry naming who did it
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 18:46'
updated_date: '2026-10-10 20:05'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** The audit log (ADR-153) is the record behind the "transparency" differentiator. But the two events an auditor or data-protection officer asks about first are missing from it.

1. **A send fired directly is not audited.** SEND_FIRED (backend/app/audit/service.py:126) is written only when a send runs through an approval (backend/app/approvals/actions/send_fire.py, ActionResult audit_action). The direct send route in backend/app/delivery/router.py records nothing; the only audit calls there are for release, :328 and :334. The same holds for the old Jinja send route (backend/app/frontend/router.py around :1918-1935). So a person sending directly, or an integration allowed to send unattended, leaves no trace in the audit log.
2. **A consent change does not say who made it.** ConsentEventDB (backend/app/recipients/db_models.py around :48-70) keeps recipient, brand, channel, purpose, status, source and note, but no actor. backend/app/recipients/router.py writes no audit entry, and the audit vocabulary has no consent action.

Decided by the user in the 2026-10-09 interview review (business baseline P2-D1); both are required before public beta (launch gate 11).
- Every send fire, by any path, writes send.fired with its actor: a person or an integration.
- Every consent write made by a person or an integration writes an audit entry with its actor.
- Recipient-initiated unsubscribes stay in the consent history, which already says source "unsubscribe"; the recipient is not an actor in the audit log.
- Exports follow when an export exists.

Final-design pass: the audit detail must not contain email addresses (ADR-153's 2026-10-08 addendum enforces this at write time); bulk consent imports may want one entry per batch rather than one per person.

Source: docs/business-interview-baseline.md → P2-D1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A send fired directly by a person writes send.fired with that person as actor
- [ ] #2 A send fired by an integration writes send.fired with the integration as actor
- [ ] #3 A consent write through the API by a person or integration writes an audit entry with its actor
- [ ] #4 A recipient's own unsubscribe writes no audit entry and stays in the consent history
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. audit/service.py:
   - add CONSENT_RECORDED = 'consent.recorded';
   - add actor_of(request), which returns (actor_type, actor_id): the integration on the JSON plane, else the signed-in person. record_from_request uses it, so the two cannot disagree.
2. Sends, audited at the routes that fire them. send_send_instance itself stays actor-free, and the approval path already audits send.fired with the approver as actor.
   - delivery/router.py: the send route records send.fired with detail send_instance_id, outcome and via 'direct', after a send that ran (a 409 refusal fired nothing). process-due records one send.fired per triggered send, with via 'scheduled'.
   - frontend/router.py (Jinja): the send route and process-due, the same way.
3. Consent, audited where the event is written:
   - recipients/service.py: create_recipient and sync_consent_from_crm take an optional keyword actor=(type, id). When they write a consent event they record consent.recorded on the recipient, with detail status, channel, purpose, source and brand. No email (ADR-153).
   - recipients/router.py passes actor_of(request).
   - Not covered: the provider webhook suppression (not a person or integration) and the recipient's own unsubscribe (stays in the consent history), as decided.
4. Tests first:
   - backend/tests/test_send_consent_audit.py: a person's JSON send; an unattended integration's send; a Jinja send; process-due by an integration; a refused send writes nothing; a CRM sync by an integration; a recipient created with consent by a person; an unchanged create writes nothing; an unsubscribe writes nothing.
5. Mutation-check, full suite, Ruff, commit, CI. Gate 11 in LAUNCH-GATES.md closes with it.
<!-- SECTION:PLAN:END -->
