---
id: TASK-89
title: >-
  Add a bulk-remove-by-criteria function mirroring `bulk_add_members`
  (`audience/service.py:125-134`) — currently only bulk-add exists, no
  bulk-remove counterpart.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 204200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Add a bulk-remove-by-criteria function mirroring `bulk_add_members` (`audience/service.py:125-134`) — currently only bulk-add exists, no bulk-remove counterpart. Should track which criteria added each member (e.g. a `source_criteria` column on `AudienceGroupMemberDB`) so that removing one criterion only removes recipients who aren't still validly in the group via a *different* active criterion, rather than blanket-removing anyone matching the criteria being un-applied. Needs some design thinking, not fully spec'd yet — not necessarily ADR-level, but more than a one-line fix. Related: the criteria-preview (`find_by_criteria`, `service.py:112-118`) currently has no `.distinct()`, so a recipient matching via multiple preference rows for the same category appears twice — rather than dedup that away, surface *which* criteria matched each recipient in the preview too (reusing the same source-criteria tracking), so a manager can see why someone's in a segment before removing a criterion. Source: [[Interview Prep - Content, Campaigns, Audience]] → Audience Q2, Q4.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 254, section "Features", position 42 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
