---
id: TASK-225
title: Override reason is prose — preset analysis wants a constrained code
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 209000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** `reason` is prose; preset analysis wants a constrained code.

| # | Gap | Where |
|---|---|---|
| 19 | `reason` is prose; preset analysis wants a constrained code | `overrides/db_models.py` |

Source: [[Variant Editor - design interview]] → What Cluster 3 produced, gap 19.

**Verified against the code 2026-09-27:** `reason = Column(String(1000), nullable=True)` at `backend/app/overrides/db_models.py:63`; typed `str | None` at `backend/app/overrides/models.py:16,26`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
