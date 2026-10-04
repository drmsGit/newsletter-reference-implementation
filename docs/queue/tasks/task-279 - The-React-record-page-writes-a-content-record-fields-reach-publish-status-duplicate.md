---
id: TASK-279
title: >-
  The React record page writes a content record: fields, reach, publish, status,
  duplicate
status: To Do
assignee: []
created_date: '2026-10-04 18:25'
updated_date: '2026-10-04 18:25'
labels:
  - frontend
dependencies:
  - TASK-276
  - TASK-277
type: feature
ordinal: 200160
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-274 design session (2026-10-04, the user) and recorded in [[Content Write Surface - final design pass]]. The record page in the React client (`frontend/src/screens/ContentDetail.tsx`, read-only today) becomes where a record is written. The Manager Workflow interview made the content screen "the primary authoring surface", full-featured; the composer's edit-in-place is "an accommodation" ([[Manager Workflow - design interview]] Q4, lines 559-562).

**What to build:**
- **Title and description**, editable.
- **Channel fields in labelled sections down the page, not tabs.** Every channel is always visible and can be collapsed by hand; fields follow the manifests' declared order (MW Q2, lines 478-499). Labels come from `GET /content/fields` (task-271), grouped by `channel`. Depends on task-276 for the order.
- **Autosave on blur**, the variant editor's model (design pass D1). Each save is `PATCH /content/{id}` with that field's channel group in `groups` and `If-Match: updated_at` (task-257). A 409 is shown on the field with "load their version", as `SaveState` does. Push's empty-means-absent rule (`without_empty_presence_fields`, inventory B18) must survive: clearing a push field removes it.
- **Reach, as a passive line above the fields**, with no confirmation: "Edits here change this record for N unsent campaigns; sends use the published version", from `GET /content/{id}/unsent-campaigns` (task-224), linking to the "Used in" section (task-267).
- **Publish**: the composer's notice and one-click Publish (design pass D5) at the top, plus a compact read-only version list lower down (number, who, when), each openable to see what it said. No restore or compare. [[ADR-128 — Version Content for Auditability and Restoration]] names restoration; deferring it was the user's choice. `GET /content/{id}/versions` must answer 404 for another brand first (task-277).
- **Status** (activate or deactivate) through `PUT /content/{id}/status`. That route takes no version token but bumps `updated_at`, so the page must refetch the record after a status change, or the next field save is refused as stale.
- **Duplicate to another brand** through `GET /content/{id}/duplicate-targets` and `POST /content/{id}/duplicate`. The copy has no published version; say so after duplicating.
- **A placeholder in each channel section** where the per-channel readiness mark will go (task-282).

**Not here:** delete (waits for task-117), categories (task-280), creating a record (task-281), readiness itself (task-282), the image picker (task-91, task-112), facets (task-207).

Tests per screen convention (`stubFetch` per route), mutation-checked.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Title, description and every channel field are editable in labelled sections in manifest order, saving on blur with the version check
- [ ] #2 A passive reach line and the unpublished notice with Publish sit above the fields, and a read-only version list below
- [ ] #3 Status can be changed and the record duplicated to another brand, and a later field save is not refused as stale
<!-- AC:END -->
