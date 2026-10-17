---
id: TASK-406
title: >-
  seed_pending_actions.py ends by sending the reader to /ui/approvals, the
  frozen Jinja page, not the manager's approvals
status: To Do
assignee: []
created_date: '2026-10-17 17:34'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced 2026-10-17 by the trailer pre-production checks (a side session's results file, docs/design/trailer/PREPRODUCTION-CHECKS.md section 3.1, with section 9 item 5), where the script was run against a scratch database. Re-checked on main (cf3fab0).

**What happens.** backend/scripts/seed_pending_actions.py ends by printing "Open /ui/approvals — 'Waiting' by default, 'Decided' for the rest." (line 184). `/ui/approvals` is the frozen server-rendered Jinja page (backend/app/frontend/router.py:3787), the old plane. The surface people are meant to use is the manager app, whose routes are `/approvals`, `/approvals/:id` and `/approvals/history` under `/manager/` (frontend/src/App.tsx:71-76). Anyone who runs the script to get demo requests to look at is told to open the wrong place, and the wording follows the Jinja filters: the manager's inbox is the waiting list and its second view is the decision history (frontend/src/screens/Approvals.tsx:82-110), not "Decided". The script came with the first approvals action (commit d1a91e7), when the Jinja page was the approvals page, and its hint was never moved when the manager took over.

**The same path elsewhere, for whoever fixes it to look at, not part of the acceptance criteria unless decided.** backend/main.py:677 returns `"review": f"/ui/approvals/{held.id}"` in the 202 body an integration gets when its request is held. That is a field a caller may follow, so it is more than a hint in a dev script, and it points at a Jinja detail page. Whether the Jinja approvals pages stay at all is TASK-312 (retiring the frozen Jinja UI, undecided), so changing that field should be decided together with it. backend/app/frontend/router.py:1464 redirects within the Jinja flow itself and is not stale.

Small enough that it needs no design pass beyond reading the manager's tab names before writing the line. Not a duplicate: nothing in the queue or docs/queue/completed names this script's closing line (task-259 only mentions the script in passing).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The closing line of seed_pending_actions.py names the manager approvals page and its two views as the manager calls them
- [ ] #2 No /ui/approvals remains in backend/scripts
- [ ] #3 The task notes say what was decided about the review field in backend/main.py, together with TASK-312
<!-- AC:END -->
