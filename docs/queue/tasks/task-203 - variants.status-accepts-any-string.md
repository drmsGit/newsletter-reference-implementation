---
id: TASK-203
title: variants.status accepts any string
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** `variants.status` accepts any string. The interview settled its values: **`variants.status` is two values (4.6)** — `draft` and `ready`, constrained in code the way `CONTENT_STATUSES` is. `approved` belongs to the send, `sent` to send instances, `archived` to the data-lifecycle ADR. `ready` is question 4.7's assertion given a home, and it is the column the variant list reads instead of recomputing completeness.

| # | Gap | Where |
|---|---|---|
| 25 | `variants.status` accepts any string | `campaigns/service.py:191` |

Source: [[Variant Editor - design interview]] → What Cluster 4 produced, gap 25 (Q4.6).

**Verified against the code 2026-09-27:** the column is `String(50)` at `backend/app/campaigns/db_models.py:62`; the service takes `status: str = "draft"` at `backend/app/campaigns/service.py:191` (`create_campaign`) and `:269` (`create_variant_for_campaign`); the API models type it `str` at `backend/app/campaigns/models.py:19,29,41,53`; the router passes it straight through (`backend/app/campaigns/router.py:83,120`). No Literal or enum anywhere in `backend/app/campaigns/`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
