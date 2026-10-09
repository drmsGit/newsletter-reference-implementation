---
id: TASK-341
title: An integration's unattended sends have no size ceiling of their own
status: To Do
assignee: []
created_date: '2026-10-09 18:47'
updated_date: '2026-10-09 18:52'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Whether an integration may fire a send without a person is a single on/off switch (backend/app/auth/dependencies.py around :635-637). The only size limit is the company-wide recipient cap, 1000 by default (backend/app/settings/service.py around :45 and :130). So an integration trusted with unattended sending can send to as many people as the whole company may. The risk is modelled by who calls, not by how big the send is. That inverts the 2026-07-05 business decision that friction follows scale or anomaly (playbook §5, finding B2).

Decided by the user in the 2026-10-09 interview review (business baseline P2-G1; recorded in a 2026-10-09 addendum to ADR-166): an integration allowed to send unattended gets its own recipient ceiling. At or below it, the send runs unattended. Above it, the send is held for a person's approval like any other held request (ADR-142 §4). The ceiling is a per-integration value bounded by the company-wide cap. Decided now, built later.

Left to the final-design pass:
- the default ceiling, and whether the existing switch becomes "ceiling above 0";
- where the ceiling is set and who may set it;
- how an over-ceiling held send reads in the inbox.

Source: docs/business-interview-baseline.md → P2-G1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An unattended send at or below the integration's ceiling runs without approval
- [ ] #2 An unattended send above it is held for a person's approval
- [ ] #3 The ceiling can be set per integration and never exceeds the company-wide cap
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from writing the ADR-166 addendum, open for the final-design pass:
(1) The hold is raised in a dependency that sees only path parameters (backend/app/auth/dependencies.py:646-648). A send's size lives in its planned executions and can change when the audience is re-resolved, so which count the ceiling compares against, and when, is open.
(2) sends.execute also guards /delivery/process-due and /delivery/send-test (backend/app/auth/policy.py:144 and :249). Neither is in APPROVABLE_ROUTES (:332-335), so an integration without unattended sending is refused them outright rather than held. process-due fires a batch of sends in one request, so how the ceiling applies to a batch is open.
<!-- SECTION:NOTES:END -->
