---
id: TASK-345
title: 'The AI spend cap never refills, and an AI run does not record who triggered it'
status: To Do
assignee: []
created_date: '2026-10-09 19:06'
updated_date: '2026-10-09 19:08'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201070
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The AI spend cap is measured against every billable run ever recorded. backend/app/ai/service.py tokens_used (around :89-104) sums the whole ledger, so once the cap is used up it never refills. A company that budgets monthly cannot express that. AIRunDB (backend/app/ai/db_models.py around :50-72) also does not record who triggered a run, so spend cannot be split by person after the fact. ADR-144 (around :113) still says the cap is "per role/user", although one company-wide pot was decided in ADR-150's 2026-09-15 addendum.

Decided by the user in the 2026-10-09 interview review (business baseline P2-H2; 2026-10-09 addendum to ADR-144):
- one company-wide pot;
- it resets each calendar month by default;
- the period is a company setting, for example month, quarter or lifetime;
- every AI run records who triggered it, a person or an integration.

No per-person budget is decided. Decided now, built later. Related, not superseded: task-75 (read the remaining budget from the company's AI source).

Left to the final-design pass:
- the time zone of "calendar month";
- a run in flight at the reset;
- how old runs without an actor are shown.

Source: docs/business-interview-baseline.md → P2-H2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The spend counted against the cap covers only the current period, monthly by default
- [ ] #2 The period is a company setting
- [ ] #3 Every new AI run records the person or integration that triggered it
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from the ADR-144 addendum, open for the final-design pass:
(1) A run started by a sweep or scheduled job, with no request behind it (ADR-153's ACTOR_SYSTEM), has neither a person nor an integration. Say how it is recorded.
(2) ADR-144 point 5's buffer 'strictly bound to user role/permission' is not reinterpreted by the addendum; with one company pot its meaning is unclear.
(3) Changing the period is a settings write, so a person makes it (ADR-150, 2026-10-02 second addendum, point 2).
<!-- SECTION:NOTES:END -->
