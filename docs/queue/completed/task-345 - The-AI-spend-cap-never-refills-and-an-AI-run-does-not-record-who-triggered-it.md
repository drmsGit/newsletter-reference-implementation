---
id: TASK-345
title: 'The AI spend cap never refills, and an AI run does not record who triggered it'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 19:06'
updated_date: '2026-10-11 15:28'
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
- [x] #1 The spend counted against the cap covers only the current period, monthly by default
- [x] #2 The period is a company setting
- [x] #3 Every new AI run records the person or integration that triggered it
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11, decided with the user one question at a time (closes the open list of ADR-144's 2026-10-09 addendum):
- D1 Periods start at 00:00 UTC (the 1st of the month, quarter or year); no company time-zone setting is added. The settings screen says so.
- D2 A run counts in the period it is recorded in, which is when the model answers. A run spanning the reset lands in the new period; nothing new is stored.
Settled in the pass:
- The period setting is one of month (default), quarter, year, lifetime (today's behaviour). A settings write by a person under settings.manage, audited.
- Every new AI run records actor_type and actor_id: a user, an integration, or system (a sweep or scheduled job, ADR-153's ACTOR_SYSTEM) with no id. Runs from before this show as "not recorded".
- ADR-144 point 5's role-bound buffer stays as the 2026-10-09 addendum left it, outside this task.

Where it lands:
1. Migration 0047: ai_runs.actor_type (String 20, nullable), ai_runs.actor_id (nullable).
2. ai/service.py: run_task(..., actor_type, actor_id) records them; period_start(db) from the setting (UTC); tokens_used and spend_to_date count runs from period_start on (lifetime: everything).
3. ai/tasks/subject_preheader.suggest and ai/orchestration pass requested_by_type/id through.
4. settings/service.py: AI_BUDGET_PERIOD_KEY, AI_BUDGET_PERIODS, get/save; ai_budget_status carries period and period_start. settings router: PUT /settings/ai/budget-period {period}, people only, audited as ai_budget_period. AIBudget model gains period and period_start.
5. Frontend: Settings, the AI budget section gets the period choice and "from <date>, periods start at midnight UTC".
6. Tests: a run before the period start is not counted; month, quarter, year boundaries in UTC; lifetime counts all; the cap's pre-call gate uses the period; each new run records the actor (person, integration); old rows read as not recorded; setting refused when unknown; audited; machine refused.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from the ADR-144 addendum, open for the final-design pass:
(1) A run started by a sweep or scheduled job, with no request behind it (ADR-153's ACTOR_SYSTEM), has neither a person nor an integration. Say how it is recorded.
(2) ADR-144 point 5's buffer 'strictly bound to user role/permission' is not reinterpreted by the addendum; with one company pot its meaning is unclear.
(3) Changing the period is a settings write, so a person makes it (ADR-150, 2026-10-02 second addendum, point 2).

2026-10-11, built. Commits ed6e96c (ADR-144 addendum 2026-10-11) and 1d7dd4c.

Decided with the user (D1, D2): periods start at midnight UTC; a run counts in the period it is recorded in (when the model answers). Settled in the pass: month (default), quarter, year, lifetime; actor user, integration or system; old runs "not recorded"; the role-bound buffer left as before.

Where it landed:
- Migration 0047: ai_runs.actor_type, actor_id. Applied to dev.
- ai/service.py: now(), period_start(db) (UTC; None for lifetime), _in_period(); tokens_used and spend_to_date count the current period; run_task records actor_type/actor_id on every recorded run (blocked, error, ok).
- ai/tasks/subject_preheader.suggest and ai/orchestration pass requested_by_type/id through to the run.
- settings/service.py: AI_BUDGET_PERIOD_KEY, AI_BUDGET_PERIODS, get/save_ai_budget_period (unknown refused); ai_budget_status carries period and period_start. Settings router: PUT /settings/ai/budget-period (people only, audited as ai_budget_period, 422 for unknown). AIBudget gains period and period_start.
- Frontend: the AI section shows "since <date>" (or "in total") beside tokens used, and a "The token budget refills" choice with the UTC note.
- Tests: test_ai_budget_period.py (18); test_settings_api's audit coverage gains the route; Settings.test for the choice.

Verification: backend 1871 passed, Ruff clean; frontend 269 passed, tsc and eslint clean; 6 mutations caught (the actor on a successful run only after adding that test). Live check 2026-10-11: Settings shows "0 of 500.000 (0%) since 1.10.2026" and the period choice set to every month with the UTC note; the user's settings were not changed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The AI spend cap counts only the current period (month by default; quarter, year or lifetime), starting at midnight UTC, with a run counted in the period it was recorded in; the period is a company setting on Settings, audited; every new AI run records who started it (user, integration or system). Decided with the user and recorded in an ADR-144 addendum. Verified by 1871 backend and 269 frontend tests, 6 mutation checks, green CI (1d7dd4c) and a live view of the settings.
<!-- SECTION:FINAL_SUMMARY:END -->
