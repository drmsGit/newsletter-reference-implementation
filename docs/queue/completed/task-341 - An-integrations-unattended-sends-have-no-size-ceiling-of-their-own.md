---
id: TASK-341
title: An integration's unattended sends have no size ceiling of their own
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:47'
updated_date: '2026-10-11 12:06'
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
- [x] #1 An unattended send at or below the integration's ceiling runs without approval
- [x] #2 An unattended send above it is held for a person's approval
- [x] #3 The ceiling can be set per integration and never exceeds the company-wide cap
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11, decided with the user one question at a time (closes the open list of ADR-166's 2026-10-09 addendum):
- D1 The switch becomes a number: unattended_ceiling per integration, how many recipients it may send to without a person. 0 = never (the default, today's off). The screen suggests 100 when it is switched on. Integrations switched on today get the current company cap at migration, so nothing changes until someone lowers it.
- D2 Raising the ceiling (from 0 or a lower number) follows today's switch-on rule: integrations.manage AND holding every grant the integration has (require_holds_integration). Lowering, down to 0, needs integrations.manage only. Both audited with the old and new value. Never above the company cap.
- D3 The count compared is the count as of now: the audience resolved again, read-only, with the send's purpose (ADR-195), or the planned recipients of a send without an audience group. Above the ceiling the fire request is held (ADR-142 §4), with the number in the inbox.
- D4 /delivery/process-due called by an integration: each due send is checked on its own; at or below the ceiling it fires, above it becomes its own held request (send.fire_send_instance), stays scheduled, and the response lists it as held.

Where it lands:
1. Migration 0045: integrations.unattended_ceiling INTEGER NOT NULL DEFAULT 0, set to the company cap where may_send_unattended, then may_send_unattended dropped. Model updated.
2. auth/integrations.py: set_unattended_ceiling (bounded 0..company cap), set_unattended_by_person gating raises only; integrations_router PUT /{id}/unattended takes {ceiling}; IntegrationOut.unattended_ceiling; audit detail {from, to}. Jinja form (frozen route): on = 100 (or keeps a higher current value), off = 0.
3. delivery/service.py: recipients_now(db, send_instance) (audience re-resolved read-only, else planned executions); process_due_scheduled_sends(db, brand_id, ceiling=None) returns triggered and held (with counts) without firing the held.
4. auth/dependencies.py: for sends.execute by an integration: the fire route is held when recipients_now > ceiling (payload carries held_for_size {recipients, ceiling}); send-test needs a ceiling of at least 1 (one recipient), else refused as today; process-due passes through and the route holds per send.
5. delivery/router.py process-due: for an integration, holds each over-ceiling send via request_approval (send.fire_send_instance, summary naming the size) and reports held ids; a person's call is unchanged (no ceiling).
6. approvals send_fire: summary and describe say "held for its size: N recipients now, above this integration's unattended limit of C" when the payload says so.
7. Tests: at/below fires unattended, above held with the size in the inbox; growth after planning counts; process-due holds one and fires the rest; ceiling bounded by the cap; raising gated, lowering not; migration keeps switched-on integrations at the cap; send-test with 0 refused.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from writing the ADR-166 addendum, open for the final-design pass:
(1) The hold is raised in a dependency that sees only path parameters (backend/app/auth/dependencies.py:646-648). A send's size lives in its planned executions and can change when the audience is re-resolved, so which count the ceiling compares against, and when, is open.
(2) sends.execute also guards /delivery/process-due and /delivery/send-test (backend/app/auth/policy.py:144 and :249). Neither is in APPROVABLE_ROUTES (:332-335), so an integration without unattended sending is refused them outright rather than held. process-due fires a batch of sends in one request, so how the ceiling applies to a batch is open.

2026-10-11, built. Commits 9c16ef7 (ADR-166 addendum 2026-10-11, the final-design pass) and 9a66286.

Decided with the user one question at a time (D1-D4 in the plan): the switch becomes a number, 0 = never, switched-on integrations keep the company cap; raising gated like switching on, lowering not; the count as of now; the batch decided send by send.

Where it landed:
- Migration 0045: integrations.unattended_ceiling (default 0), set to the company cap where may_send_unattended, which is dropped. Applied to dev: webshop (switched on) got 250, the dev cap; the others 0.
- auth/integrations.py: unattended_ceiling(), set_unattended_ceiling (0..company cap, ValueError outside), set_unattended_by_person gates raises only; SUGGESTED_UNATTENDED_CEILING 100.
- integrations_router: PUT /integrations/{id}/unattended takes {ceiling}; 422 above the cap; IntegrationOut.unattended_ceiling; audit detail {from, to}. Jinja route (frozen): on = 100 within the cap, off = 0; the page shows "up to N recipients".
- auth/dependencies.py _held_by_ceiling: for sends.execute by an integration: 0 holds every send; the fire route holds when recipients_now > ceiling, with held_for_size {recipients, ceiling} in the payload; send-test needs a ceiling of at least 1; process-due passes through.
- delivery/service.py recipients_now (audience resolved again with the send's purpose, or recipients still to send, status created); process_due_scheduled_sends(ceiling, held) skips and reports over-ceiling sends.
- delivery/router.py process-due: an integration's call holds each over-ceiling send (request_approval, the send-firing action) and returns held_send_instance_ids; a person's call has no ceiling. held_summary() adds the size to the inbox line, also used by the guard's handler in main.py.
- approvals send_fire describe: a warning that it was held for its size.
- Tests: test_unattended_ceiling.py (13). Old switch callers moved to the ceiling in test_api_guard, test_brand_boundary, test_process_due_brand, test_send_outcome, test_send_consent_audit, test_integrations, test_integrations_api.

Verification: backend 1816 passed, Ruff clean; frontend 267 passed, tsc clean (schema regenerated). 10 mutations, all caught after adding two cases (0 holds even an empty send; recipients already sent do not count). Live check 2026-10-11: the dev Jinja integrations page shows webshop "Sends without approval up to 250 recipients" after the migration; the user's integrations were not changed. The React app has no integrations screen yet (task-358).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An integration's unattended sending is a recipient ceiling (0 = never; switched-on integrations keep the company cap). A fired send is counted as of now and held for a person above the ceiling, the inbox saying it was held for its size; the batch route holds over-ceiling sends one by one and fires the rest; raising the ceiling needs every grant the integration has, never above the company cap. Decided with the user and recorded in an ADR-166 addendum. Verified by 1816 backend and 267 frontend tests, 10 mutation checks, green CI (9a66286) and a check of the migrated dev data.
<!-- SECTION:FINAL_SUMMARY:END -->
