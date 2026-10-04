---
id: TASK-207
title: 'The facet model, including a facet-value mapping on duplicate_campaign'
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-04 10:22'
labels:
  - backend
dependencies: []
priority: p3
type: feature
ordinal: 207200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **The facet model** (Q8, 9, 9b, 12): declared facets, their values, and links from content *and campaigns* to values — per brand, governed by an administrator. Its administration surface belongs in Settings, which is **gap C2** and has no router at all, so this work inherits that dependency.

And, from Cluster 3, landing with it: **`duplicate_campaign` cannot accept a facet-value mapping** (Q8), which question 2.9b's per-brand decision requires. Lands with the facet model.

Source: [[Manager Workflow - design interview]] → What Cluster 2 produced, requirement 4, and What Cluster 3 produced, gap 11 (Q3.8).

**Decided:** [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] (accepted).

**Verified against the code 2026-09-27:** no "facet" anywhere in `backend/app/`. `duplicate_campaign` (`backend/app/campaigns/duplication.py:127-135`) takes `campaign_id`, `target_brand_id`, `name`, `content_mode` and `variant_ids` — no mapping.

Related: task-49 (gap C2, the settings surface).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-04 (task-263): the bind picker browses by category until facets exist. When this task lands, facets join the picker and the Content list as a second filter (ADR-175 addendum 2026-10-04). Its Settings-router dependency (task-49 gap C2) may be stale: backend/app/settings/router.py now exists. Verify before relying on it.
<!-- SECTION:NOTES:END -->
