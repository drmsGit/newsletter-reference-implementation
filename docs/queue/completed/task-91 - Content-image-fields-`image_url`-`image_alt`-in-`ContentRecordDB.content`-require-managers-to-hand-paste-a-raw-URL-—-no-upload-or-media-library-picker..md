---
id: TASK-91
title: >-
  Content image fields (`image_url`/`image_alt` in `ContentRecordDB.content`)
  require managers to hand-paste a raw URL — no upload or media-library picker.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 19:05'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 204400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Content image fields (`image_url`/`image_alt` in `ContentRecordDB.content`) require managers to hand-paste a raw URL — no upload or media-library picker. Carried over from a past Condor implementation; a marketer shouldn't need to copy/paste image URLs. Needs an "upload / select image" UI component (upload to storage, or pick from previously-uploaded images) wired into the content create/edit forms, replacing the plain URL text input. New feature, not a bug — low priority, no rush. Source: user feedback while reviewing the content-schema redesign, 2026-07-12.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 258, section "Features", position 44 in that section (top = do next). The description is the original entry, verbatim.

Closed 2026-10-08 in the pre-review queue cleanup, without a build of its own: merged into task-112 (asset and media management), which describes the same gap and holds its 2026-09-27 design. This entry's text is copied verbatim into task-112's notes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Not built on its own: merged into task-112, the asset and media management task, which carries this entry's text. Closed in the 2026-10-08 queue cleanup.
<!-- SECTION:FINAL_SUMMARY:END -->
