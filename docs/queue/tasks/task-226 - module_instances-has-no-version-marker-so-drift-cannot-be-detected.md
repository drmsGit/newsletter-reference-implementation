---
id: TASK-226
title: 'module_instances has no version marker, so drift cannot be detected'
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 209100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** `module_instances` has no version marker, so drift cannot be detected. The interview chose to say so rather than work it out: a snapshot **warns** about unpublished drift with an offer to publish, rather than resolving it silently (4.3).

| # | Gap | Where |
|---|---|---|
| 22 | `module_instances` has no version marker, so drift cannot be detected | `campaigns/db_models.py` |

Source: [[Variant Editor - design interview]] → What Cluster 4 produced, gap 22 (Q4.3).

**Verified against the code 2026-09-27:** `ModuleInstanceDB` (`backend/app/campaigns/db_models.py:72-101`) has `id`, `variant_id`, `module_type`, `position`, `content_record_id`, `module_data`, `decision_slot_id`, `created_at` and `updated_at` — no version marker.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
