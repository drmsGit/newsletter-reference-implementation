---
id: TASK-262
title: >-
  "Overridden by X" on campaign detail is module-wide, so a catalogue edit to
  another field reads as an override
status: To Do
assignee: []
created_date: '2026-10-03 18:56'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reported by the user 2026-10-03: "if I directly change a content in catalog (because I forgot to click override) the comment still says overridden by ds@... but I haven't used override but changed the full content record". The audit log shows what happened: module 39 had headline_medium overridden at 18:48 (override 5, active), and body_medium was edited in the catalogue at 18:49. frontend/src/screens/CampaignDetail.tsx:131 renders "Overridden by <overridden_by>" for the whole module whenever an active override exists, naming neither the fields nor that other fields are the catalogue's. ADR-178 point 4 wants overridden state legible per field.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Campaign detail names which fields of a module are overridden, and a module with none says nothing about overrides
<!-- AC:END -->
