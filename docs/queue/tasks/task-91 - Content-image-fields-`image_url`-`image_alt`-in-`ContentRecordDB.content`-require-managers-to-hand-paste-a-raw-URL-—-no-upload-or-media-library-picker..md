---
id: TASK-91
title: >-
  Content image fields (`image_url`/`image_alt` in `ContentRecordDB.content`)
  require managers to hand-paste a raw URL — no upload or media-library picker.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
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
<!-- SECTION:NOTES:END -->
