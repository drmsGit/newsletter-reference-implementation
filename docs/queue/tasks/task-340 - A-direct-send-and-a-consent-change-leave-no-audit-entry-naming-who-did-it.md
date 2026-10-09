---
id: TASK-340
title: A direct send and a consent change leave no audit entry naming who did it
status: To Do
assignee: []
created_date: '2026-10-09 18:46'
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
