---
id: TASK-205
title: A read-only candidate count for a decision slot
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200390
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **A read-only candidate count for a decision slot** (Q4b). `POST /decision/slots/{id}/execute` resolves for real and writes a `DecisionResolution`, so there is no way to ask what a slot would choose between without causing a decision.

Source: [[Manager Workflow - design interview]] → What Cluster 2 produced, requirement 2 (Q2.4b).

**Verified against the code 2026-09-27:** `backend/app/decision/router.py:25-40` is the only slot route. `execute_decision_slot` (`backend/app/decision/service.py:12`) updates a resolution in place (`:90-96`) or creates one (`:104-113`). There is no count or dry-run route.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
