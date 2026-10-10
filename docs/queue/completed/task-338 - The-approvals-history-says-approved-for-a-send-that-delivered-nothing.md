---
id: TASK-338
title: The approvals history says 'approved' for a send that delivered nothing
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:26'
updated_date: '2026-10-10 20:39'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200760
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The approvals history's Outcome column shows only the request's own status (frontend/src/screens/Approvals.tsx:42). An approved send runs through backend/app/approvals/actions/send_fire.py, whose result message already states the outcome first: "Partly failed: N delivered, M failed, K excluded" (around :226-233, task-323). But that message is not stored on the request. PendingActionDB keeps only execution_error (backend/app/approvals/db_models.py:130), which is set when the action itself fails. So a send in which every delivery failed reads "approved" in the history.

Decided with the user 2026-10-09 (interview review of the Manager Workflow design interview, Cluster 1 Q6, the outcome point deferred to a "Q5 revisit" that never picked it up; see the interview at about :328-330): the history shows what the approved action ended in, as a plain fact, linked to its subject (the send). The approver is not notified; following up failures belongs to monitoring (the deliveries screen), not to whoever approved. A send's outcome can also change after the approval ran, through a retry or a release (ADR-192). The final-design pass decides whether the history shows the result at run time or reads the send's current status.

Source: [[Manager Workflow - design interview]] → Cluster 1, Q6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The approvals history shows an approved send's outcome (sent, partly failed, failed) with counts
- [x] #2 The entry links to the send
- [x] #3 No notification is sent to the approver
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit 64c5761).

Final-design decision by the user: show the send as it is NOW, read live, not frozen at approval. No migration.

What changed:
- An action may offer an optional outcome(db, subject_id, *, brand_id) hook. send_fire's version reads the SendInstance live through the brand check (subject_in_brand) and words it with said(status, send). That is the same function execute() now uses for its result message, so the two cannot drift.
- PendingActionRow.outcome is filled by the router only for approved requests.
- The React history shows 'status — outcome', with the outcome linked to /deliveries/{subject_id} for a send_instance subject. The link is built in the client from the subject type.
- No notification, as decided.

Tests:
- Backend: backend/tests/test_approval_outcome.py, 3 tests, all failing first (no field). An approved send that failed says 'Failed: 0 delivered, 2 failed, 0 excluded.'; a later status change shows; a rejected request has none.
- Frontend: 1 test in Approvals.test.tsx (the link).

Mutations, each caught:
- the router never asks: 2 failed;
- every status asks: 1;
- frozen, not live: 1;
- frontend outcome hidden: 1.

Suites: backend 1655, frontend 250, Ruff, tsc, ESLint. CI green on 64c5761.

No live check: it would need an approved send in the user's dev data, which means firing a mock send at demo recipients. Offered to the user rather than done.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The approvals history now says what an approved send ended in, e.g. 'approved — Partial failed: 940 delivered, 60 failed, 0 excluded.', linked to the send, and nobody is notified. Read live through a new optional outcome hook on actions (decided 2026-10-10), so a later retry or release shows; the wording is shared with the approval's own run message. Verified by new backend and frontend tests (failed first, four mutations caught), the full suites, and green CI on 64c5761.
<!-- SECTION:FINAL_SUMMARY:END -->
