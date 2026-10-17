---
id: TASK-403
title: >-
  A held AI subject run that was blocked or failed still raises an approval
  request with nothing in it to approve
status: To Do
assignee: []
created_date: '2026-10-17 17:34'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced 2026-10-17 by the trailer pre-production checks (a side session's results file, docs/design/trailer/PREPRODUCTION-CHECKS.md section 3.2, with section 9 item 2), run on a scratch database; the user asked for the defects to be queued, not fixed there. Re-checked on main (cf3fab0) by reading the code.

**What happens.** `suggest_subject_for_variant` (backend/app/ai/orchestration.py:53) calls `subject_task.suggest`, which returns `(options, run)` where `run` is a `TaskRun` (backend/app/ai/tasks/subject_preheader.py:183-221). `run.ok` is False whenever `run_task` did not produce a result: no published prompt (backend/app/ai/service.py:254-260, "No published prompt for this task — publish one in Settings."), a cost that could not be verified up front (service.py:276-284), a worst case over the spend cap (service.py:298-308), or a provider that answered with a failure (service.py:333-335, status error). The orchestration never reads `run.ok`. It checks `run is None` (orchestration.py:100-103), returns `inline` when the task's approval mode is not `REQUIRE_APPROVAL` (105-106), and for every other run, ok or not, raises the approval request (108-117) and returns `held` with the new request's id (126-128).

**What the person sees.** In held mode, a "Suggest with AI" press on a task with no published prompt (which is the state of a fresh install: nothing is published until someone does it in Settings) raises a request in Approvals for a run that produced nothing. The editor shows the failed run's own message and, above it, "The suggestion is waiting for approval." with a link "Open it in Approvals" to the new request (frontend/src/screens/SubjectSuggestions.tsx:45-52, 63-64). The request's detail can only say "No usable options could be read from the reply, so there is nothing to apply" and carries a `blocked_reason` (backend/app/approvals/actions/ai_subject_apply.py:115-122), so it cannot be approved. It waits until it expires or someone rejects it, and each further press raises another, because the one-open-request-per-subject index is keyed on the run id (`subject_id=run.run_id`, orchestration.py:116), which is new each time. The checks created one before publishing the prompt and it stayed waiting in the scratch database. The same happens for a cap-refused run, where the approver is asked to decide about nothing and the requester is not told the real reason.

**Inline mode is the contrast.** The default mode already lets the caller read the failed run's own message, so the manager sees "No published prompt for this task — publish one in Settings." The sibling route for topic proposals already treats a failed run as its own outcome: `{"outcome": "inline" if run.ok else "refused", ...}` (backend/app/campaigns/router.py:535). The held path is the one that skips the check.

**Where the fix could land, not decided.** The smallest: in held mode, return the run's message instead of raising the request when `run.ok` is False, keeping the `inline` outcome so both callers render it as they do today. Wider: a new outcome (the `Outcome` literal at orchestration.py:37 and both callers' mappings, backend/app/campaigns/router.py:486-499 and backend/app/frontend/router.py:1456-1466), which would change what the JSON caller and the Jinja redirect return for a blocked run in inline mode too. The approval-mode rule itself is [[ADR-141 — In-App Assistive AI Actions]] (see the module docstring, orchestration.py:14-20); the spend rules are [[ADR-144 — AI Data and Model Governance]]; neither needs an addendum for this.

Requests already raised for failed runs stay as they are and lapse; nothing needs migrating. Not a duplicate: task-387 added the in-flight refusal on the same function and left this path alone; task-125 is about decision-slot content, not this.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 In held mode, a run that did not succeed (no published prompt, cost not verifiable, over the spend cap, provider failure) raises no approval request, and the editor shows that run's own message and no link to Approvals
- [ ] #2 A successful run in held mode still raises exactly one request, and a second ask while it waits still answers duplicate
- [ ] #3 Inline mode answers a blocked run as it does today, or the change to it is stated in the task notes
- [ ] #4 A backend test with a held task and no published prompt finds no pending action, and fails when the unconditional request is restored
<!-- AC:END -->
