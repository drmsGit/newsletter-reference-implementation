---
id: TASK-229
title: No duplicate_variant — the primary creation action is unbuilt
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 209400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **Duplication is primary and does not exist.** `duplicate_campaign` and `duplicate_content_record` are built; there is no `duplicate_variant`, and 5.1 made it the primary creation action. 5.6 settles that it **reuses** the campaign machinery rather than reimplementing a subset — narrower (same-brand only), not parallel.

| # | Gap | Where |
|---|---|---|
| 27 | No `duplicate_variant` — the primary creation action is unbuilt | `campaigns/duplication.py` |
| 29 | A context-sensitive `content_mode` default (`KEEP` within a campaign) | build-time |

Gap 29 only applies once gap 27 exists, so they are one piece of work.

Source: [[Variant Editor - design interview]] → What Cluster 5 produced, gaps 27 and 29 (Q5.1, 5.6).

**Verified against the code 2026-09-27:** `backend/app/campaigns/duplication.py` defines `content_modes_for` (`:105`), `duplicate_campaign` (`:127`), `duplicate_content_record` (`:384`) and `summarise_source` (`:415`); no `duplicate_variant` anywhere in `backend/app/`. Gap 29 is partial: `content_modes_for` returns `[KEEP, LAYOUT]` within one brand and `backend/app/templates/campaign_duplicate.html:131` pre-selects the first, but `duplicate_campaign` has no server-side default — `content_mode` is required (`duplication.py:133`).

Related: task-113 (duplication must carry active overrides).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
