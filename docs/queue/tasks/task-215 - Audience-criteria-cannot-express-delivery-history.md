---
id: TASK-215
title: Audience criteria cannot express delivery history
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p3
type: feature
ordinal: 208000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **Audience criteria cannot express delivery history** (Q6). Today's four keys — `language`, `status`, `category_id`, `min_score` — are all recipient attributes. *"Campaign X was or was not delivered"* queries `DeliveryExecutionDB`, so criteria would span who someone **is** and what has **happened** to them. The same door opens engagement criteria.

Source: [[Manager Workflow - design interview]] → What Cluster 5 produced, gap 16 (Q5.6). The same answer is why a failed send needs no retry feature: build a segment of who missed it.

**Verified against the code 2026-09-27:** criteria evaluation (`backend/app/audience/service.py:407-414`) reads only `category_id`, `language`, `status` and `min_score`; the same keys are documented at `backend/app/audience/db_models.py:77`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
