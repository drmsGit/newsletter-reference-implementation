---
id: TASK-387
title: >-
  The server refuses a second paid AI run for the same thing while one is still
  running
status: To Do
assignee: []
created_date: '2026-10-16 18:34'
updated_date: '2026-10-16 18:34'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200775
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced 2026-10-16 in the task-100 design pass (user: file it, do not build it there). task-100 made every model call in the React client one-request-at-a-time: frontend/src/components/AIButton.tsx ignores presses while a call runs (React Aria isPending). That protects one button in one tab, and nothing more. Two open tabs on the same variant, a double-fired request from a flaky network retry, or an integration script can still start two generations for one target at the same time, and each is paid: POST /campaigns/variants/{id}/suggest-subject (backend/app/campaigns/router.py:448) calls suggest_subject_for_variant (backend/app/ai/orchestration.py:53), which calls subject_task.suggest (orchestration.py:86; backend/app/ai/tasks/subject_preheader.py:183) with no check for a run already in flight on that variant. The spend cap (backend/app/ai/service.py:181 run_task, hard stop near line 244) bounds the total damage but does not prevent the waste, and it checks the ledger before either call has written its tokens, so two concurrent calls can both pass it. The candidate shape: a per-target guard in the shared AI path (run_task, not each task), for example a transaction-scoped advisory lock keyed on task and target, as the lock-out guard in backend/app/auth/service.py _lock_access does, answering a second request with a 409 that says a suggestion for this is already being written. Open questions for its final-design pass: whether the second request should wait and receive the first one's run instead of a refusal; whether the lock must be held across the provider call (seconds long, so a session-level lock and its release on failure need care); and how this sits with task-124 (the contention model, needs-adr), whose human-versus-AI part this is a narrow first case of. tasks 368 to 370 add three more paid AI actions that go through the same path, which is why it belongs in run_task once. ADR-144 (the budget) is the record that would carry the rule, as a dated addendum.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Checked 2026-10-16 when filed: run_task reads tokens_used (backend/app/ai/service.py:239), calls provider.generate (line 257) and records the run only afterwards, so two concurrent calls see the same remaining budget.
<!-- SECTION:NOTES:END -->
