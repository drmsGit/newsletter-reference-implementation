---
id: TASK-387
title: >-
  The server refuses a second paid AI run for the same thing while one is still
  running
status: Done
assignee:
  - '@claude'
created_date: '2026-10-16 18:34'
updated_date: '2026-10-17 08:23'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. run_task records the run as running before the model call, its input and output tokens holding the worst case, after a claim under a transaction-scoped advisory lock: expire runs running for over 10 minutes (error, never finished), refuse when the same task already runs for the same target (RunInFlight, nothing recorded), check the cap against tokens used including running runs, insert the running row, commit. 2. After the call, the row gets its real tokens, status, output, and created_at = clock_timestamp (it counts in the period it is recorded in). 3. RunInFlight: 409 in words for the JSON routes (main.py handler), refused outcome for the subject orchestration (JSON and Jinja). 4. Running runs: skipped by every read-back; spend in USD counts finished runs only. 5. Tests first (claim, refusal, cap with a running run, stale expiry, period stamp, two threads at once), mutation-checked; gates; ADR-144 addendum 2026-10-17.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Checked 2026-10-16 when filed: run_task reads tokens_used (backend/app/ai/service.py:239), calls provider.generate (line 257) and records the run only afterwards, so two concurrent calls see the same remaining budget.

Built 2026-10-17 (c5a26e7) with the ADR-144 addendum 2026-10-17. Decided with the user one question at a time: a duplicate is refused in words, not held; the cap race is closed too by counting runs in flight; a run running over 10 minutes is given up. Code: backend/app/ai/service.py run_task records the run as running before the call (input and output tokens holding the counted input and the ceiling), after a claim under pg_advisory_xact_lock (expire stale runs, refuse a running run of the same task and target, check the cap with running runs counted, insert); finish() writes the real tokens, status and output and restamps created_at, so a run counts in the period it is recorded in; a provider exception marks it an error. A duplicate is also refused before the provider is asked anything (token counting is a call of its own for Claude), the check under the lock being the one that holds. RunInFlight answers 409 in words (main.py); the subject orchestration turns it into its refused outcome, Jinja redirect included. Running runs are skipped by every read-back (subject, drafts, retranslations, topic proposals) and by the USD spend; tokens_used ignores a stale running run. Tests: backend/tests/test_ai_runs_in_flight.py (10, one with two threads and a widened gap); 13 mutations, all killed after sharpening four tests. Full pytest and Ruff green locally. CI: the run with this commit was cancelled by a newer push; the next run (a9fd4d5) passed everything of this task (2170 passed) and failed only test_product_name, on the retired name in docs/design/DESIGN.md and HANDOFF.md from the parallel design commit a4ebdbb, not from this task. Live check on scratch variant 23 with a stand-in running row (no provider contact, since the refusal comes first): Suggest with AI showed the refusal in words, the running row was not listed as a suggestion, no run was recorded; the stand-in was removed afterwards.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A run is recorded as running, holding its worst case, before the model call, under a short lock: a second request for the same task and thing is refused at once in words (nothing spent), and the spend cap holds under any concurrency. Stale runs are given up after 10 minutes; running runs are no result anywhere. ADR-144 addendum 2026-10-17. Verified by 10 pytest cases (one concurrent), all mutation-checked, the full suite, and a live check on scratch variant 23; CI green for this work, red only on an unrelated retired-name check from the parallel design commit.
<!-- SECTION:FINAL_SUMMARY:END -->
