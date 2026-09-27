---
id: TASK-200
title: Nothing prevents self-approval
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: bug
ordinal: 104800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** **Nothing prevents self-approval** (Q8). `may_decide` checks the action's permission against the request's brand and never compares decider to requester. Safe only while machines requested and could not approve; a hole the moment a person can request.

Source: [[Manager Workflow - design interview]] → What Cluster 5 produced, gap 17 (Q5.8). The same cluster notes a record owed: ADR-168's build note — *"a person firing a send is the approval"* — becomes insufficient once people can request.

**Verified against the code 2026-09-27:** `may_decide` (`backend/app/approvals/service.py:345-377`) checks only `approve_permission`. Nothing in `backend/app/` compares `requested_by_id` with the decider.

Related: [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]].
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
