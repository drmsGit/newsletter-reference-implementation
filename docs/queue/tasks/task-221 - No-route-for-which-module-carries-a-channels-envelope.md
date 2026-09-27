---
id: TASK-221
title: No route for which module carries a channel's envelope
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 208600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** No route for *"which module carries this channel's envelope"* — `envelope_module_type` is internal. The composer needs it: the envelope is promoted to the top of the composer **by asking `envelope_module_type(channel)`** rather than by knowing a module called `header` is special — and push returns `None`, so the same screen is correct everywhere without a branch.

| # | Gap | Where |
|---|---|---|
| 12 | No route for *"which module carries this channel's envelope"* | `envelope_module_type` is internal |

Source: [[Variant Editor - design interview]] → What Cluster 2 produced, gap 12 (Q2.3).

**Verified against the code 2026-09-27:** `envelope_module_type` (`backend/app/modules/registry.py:208`) is used only internally — `backend/app/frontend/router.py:1063,1200`, `backend/app/campaigns/service.py:393`, `backend/app/campaigns/duplication.py:267`, `backend/app/ai/orchestration.py:76`. The modules router has two routes (`backend/app/modules/router.py:38,46`) and neither exposes it.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
