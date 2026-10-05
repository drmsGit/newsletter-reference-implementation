---
id: TASK-286
title: >-
  The picker opens on records ready for the channel, and the Content list
  filters by readiness
status: To Do
assignee: []
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 18:10'
labels:
  - frontend
dependencies:
  - TASK-283
type: feature
ordinal: 200140
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-282 design session (2026-10-05): the picker and the Content list read readiness in the first build (the ADR-174 addendum 2026-10-05, point 3; Manager Workflow Q11 and Q5). Depends on the storage task (the `ready_for` filter and per-row `ready_for` on `GET /content/`).

**The bind picker** (`BindRecord` in `frontend/src/screens/CatalogueModule.tsx`, task-269):
- it opens on records ready for the variant's channel;
- a visible switch, "Show records not ready for <Channel>", widens the list;
- rows that are not ready carry a "Not ready for <Channel>" note (MW Q11: "an unready record appears marked as unready rather than absent");
- they can still be bound. A note informs and never blocks, as the other picker notes do.

**The Content list** (`frontend/src/screens/Content.tsx`) gets a "Ready for" filter (Any, Email, Push), held in the URL like status and category.

Tests; mutation-checked; a live check (read-only for the list, a scratch record for any bind).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The picker opens on records ready for the variant's channel, with a switch to show the rest marked "Not ready for <channel>"
- [ ] #2 The Content list has a Ready for filter held in the URL
<!-- AC:END -->
