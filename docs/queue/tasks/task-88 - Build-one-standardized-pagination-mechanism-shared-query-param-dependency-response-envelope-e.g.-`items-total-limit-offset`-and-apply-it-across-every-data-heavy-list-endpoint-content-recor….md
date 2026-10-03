---
id: TASK-88
title: >-
  Build one standardized pagination mechanism (shared query-param dependency +
  response envelope, e.g. `{items, total, limit, offset}`) and apply it across
  every data-heavy list endpoint: content recor…
status: In Progress
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-03 12:02'
labels:
  - backend
dependencies: []
type: feature
ordinal: 204100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Build one standardized pagination mechanism (shared query-param dependency + response envelope, e.g. `{items, total, limit, offset}`) and apply it across every data-heavy list endpoint: content records, audience groups (`find_by_criteria`/`list_members`), content versions, decision slots/resolutions, engagement events, recipients. No pagination pattern exists today — only scattered hardcoded `.limit(20)`/`.limit(50)` calls in `frontend/router.py` with no offset/page param, no consistent shape. One offset/limit-based approach is sufficient for all of these at this project's realistic scale (none will hit true big-data volumes needing cursor/keyset pagination). Ranked reasonably high: even in the POC, presenting to people needs realistic test data volumes (recipients, events especially), and a positive UX matters in the POC too, not just "the real version." Supersedes the earlier "keep in poc" call on content-record pagination — folded in here. Source: [[Interview Prep - Content, Campaigns, Audience]] → Audience Q6 (supersedes Content Q3).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 252, section "Features", position 41 in that section (top = do next). The description is the original entry, verbatim.

2026-09-27: [[Manager Workflow - design interview]] Cluster 2 requirement 5 widens this — server-side filtering as well as paging, on content, campaigns, audiences, recipients and approvals (campaigns and approvals are not named above). Cluster 3 gap 10: GET /campaigns/decision-slots/{id}/resolutions is the worst instance (backend/app/campaigns/router.py:286-296, .all() at backend/app/campaigns/service.py:809). The approvals list's other filters are task-209.
<!-- SECTION:NOTES:END -->
