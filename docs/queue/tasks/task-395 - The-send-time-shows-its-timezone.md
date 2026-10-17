---
id: TASK-395
title: The send time shows its timezone
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 210900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-18; screenshot screenshots/72-send-schedule.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. In the send step, When, At a time shows a Send at field (frontend/src/screens/SendVariant.tsx:380) and nothing says which timezone the time is in. The field is a browser datetime-local value, read as the browser's local time and sent as UTC (new Date(at).toISOString(), SendVariant.tsx:337), so today the zone is the manager's computer's, which may not be the brand's or the audience's. To decide: which zone the time is in (the browser's, a brand setting, the recipients'), and how it is shown: beside the field, and repeated as a resolved date, time and zone before the send is planned. Recipient-local send times are a different feature and not this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The zone a send time is read in is named beside the field
- [ ] #2 Before a send is planned, its date, time and zone are shown as they will be used
<!-- AC:END -->
