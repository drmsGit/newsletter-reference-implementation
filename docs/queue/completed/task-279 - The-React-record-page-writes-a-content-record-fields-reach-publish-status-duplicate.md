---
id: TASK-279
title: >-
  The React record page writes a content record: fields, reach, publish, status,
  duplicate
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 18:25'
updated_date: '2026-10-05 11:30'
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
- [x] #1 Title, description and every channel field are editable in labelled sections in manifest order, saving on blur with the version check
- [x] #2 A passive reach line and the unpublished notice with Publish sit above the fields, and a read-only version list below
- [x] #3 Status can be changed and the record duplicated to another brand, and a later field save is not refused as stale
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. resources.ts:
   - useSaveContentRecord(recordId): PATCH a partial body with If-Match from the cache, in the same mutation scope as the composer's catalogue saves, invalidating the record subtree;
   - useContentVersions, useSetContentStatus, useDuplicateTargets, useDuplicateContent.
2. components/PublishState.tsx, moved from CatalogueModule.
3. ContentDetail.tsx, top to bottom:
   - title with a status badge and Deactivate/Reactivate (refetch after);
   - Duplicate (target select; same brand navigates to the copy, another brand shows a "no published version" notice);
   - PublishState and the reach line;
   - title and description AutosaveFields;
   - per-channel <details open> sections with AutosaveFields in declared order (PATCH {content, groups:[channel]}), undefined keys read-only below;
   - the read-only version list, openable;
   - Used in.
   The readiness slot is a code comment only (task-282).
4. Tests in ContentDetail.test.tsx: field autosave with groups and If-Match; title saves without groups; 409 reload; reach line; publish; versions; status refetch; duplicate both ways; section order; undefined key read-only. Mutation-check. Live check in the React client.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-05.
- New hooks in resources.ts: useSaveContentRecord (PATCH a partial body, If-Match read from the cache at send time, scope composer-content shared with the composer's catalogue saves, invalidating the record subtree), useContentVersions, useSetContentStatus (re-reads the record, because the status route moves updated_at without a token), useDuplicateTargets and useDuplicateContent.
- PublishState moved to components/PublishState.tsx, shared with CatalogueModule; the composer's tests are unchanged and pass.
- ContentDetail.tsx is now the record page: status and Deactivate/Reactivate, Duplicate into (same brand opens the copy; another brand says it is unpublished there), PublishState and the passive reach line, title and description autosave, per-channel <details open> sections in declared order with autosave by channel group, undefined keys read-only under "Other stored values", the read-only published versions list (openable, no restore), Used in. The readiness spot is a code comment (task-282).
- AutosaveField's field prop is narrowed to what a form needs, so a ContentField fits.
- Bug found and fixed while testing: after a refused save, "Load their version" left the refused text in the field when the stored value had not changed (somebody else edited another field), so the refused edit looked saved. Reloading now remounts the page, so every field starts from what is stored.
- Possibly the same in the variant editor's fields: not checked here; worth a look.
- Tests: ContentDetail.test.tsx rewritten with a stateful stub server that checks If-Match (13 tests). Mutation-checked against 13 mutants, each caught. Client tsc clean, vitest 153 passed. No backend change.
- Checked live in the React client:
  - record 65 renders, read-only;
  - on a scratch record 116 ("task-279 live check", created for this and left inactive), a field saved on blur and the publish notice appeared; Deactivate, then another field save, was not refused; Publish made Version 1 appear.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The React record page writes a record: title, description and every channel field autosave with the version check, in labelled sections in declared order; a passive reach line, the publish notice and a read-only version list; status and duplicate. A refused save now reloads cleanly. Verified by 13 tests mutation-checked against 13 mutants, the client suite (153), and a live run on a scratch record (save, deactivate then save, publish).
<!-- SECTION:FINAL_SUMMARY:END -->
