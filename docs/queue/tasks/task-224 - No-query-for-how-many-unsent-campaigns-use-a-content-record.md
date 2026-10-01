---
id: TASK-224
title: No query for how many unsent campaigns use a content record
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200370
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** No query for *"how many unsent campaigns use this record"*. From the resolution: **a catalogue edit being visible to other campaigns is the point of a catalogue, not a hazard.** The hazard is *silence* about reach — which is why 3.7 exists and why the count is passive.

| # | Gap | Where |
|---|---|---|
| 17 | No query for "how many unsent campaigns use this record" | new |

Source: [[Variant Editor - design interview]] → What Cluster 3 produced, gap 17 (Q3.1, 3.7).

**Verified against the code 2026-09-27:** the nearest thing is the delete guard at `backend/app/content/service.py:750-754`, which counts every `ModuleInstanceDB` row for a record with no campaign or sent/unsent filter.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
