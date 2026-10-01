---
id: TASK-216
title: No campaign-level state view — nothing answers which campaigns are in flight
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p1
type: feature
ordinal: 200340
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **No campaign-level state view** (Q4). Nothing answers "which campaigns are in flight" — *in flight* is derived from variants, snapshots and sends.

Source: [[Manager Workflow - design interview]] → What Cluster 5 produced, gap 18 (Q5.4).

**Verified against the code 2026-09-27:** `CampaignDB.status` exists (`backend/app/campaigns/db_models.py:13`, default `"draft"`) and is set only at creation (`backend/app/campaigns/service.py:191,221,232`); the send lifecycle never moves it. No in-flight route in `backend/app/campaigns/router.py`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
