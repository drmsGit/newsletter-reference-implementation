---
id: TASK-338
title: The approvals history says 'approved' for a send that delivered nothing
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 18:26'
updated_date: '2026-10-10 20:31'
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
- [ ] #1 The approvals history shows an approved send's outcome (sent, partly failed, failed) with counts
- [ ] #2 The entry links to the send
- [ ] #3 No notification is sent to the approver
<!-- AC:END -->
