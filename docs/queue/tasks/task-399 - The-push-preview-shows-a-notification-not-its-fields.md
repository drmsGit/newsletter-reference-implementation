---
id: TASK-399
title: 'The push preview shows a notification, not its fields'
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 211300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-21; screenshot screenshots/60-push-preview.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. The preview of a push variant lists push_title, push_body, push_image_url and push_link as a definition list (frontend/src/screens/Preview.tsx:97), with the image as an address. A manager cannot judge how the notification reads, what the image does, or where the text will be cut. A representative notification (title, text, image, the link it opens), clearly labelled as an approximation rather than any device's exact look, with the raw fields as secondary details. Whether to show more than one platform's truncation is a design choice.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The push preview shows the title, text and image as a notification, labelled as representative
- [ ] #2 The raw fields remain visible as details
<!-- AC:END -->
