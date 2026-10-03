---
id: TASK-261
title: >-
  Typing in a catalogue field, then pressing Override here, saves the typing to
  the catalogue and overrides with the old value
status: To Do
assignee: []
created_date: '2026-10-03 18:56'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-10-03 from the audit log of the user's own test on the dev server (module 36, record 65): content.updated at 18:45:33.958, then override.created 0.1 s later with headline_hero "" (the value before the typing). The field saves on blur (design pass D1), and pressing the "Override … here" button blurs the field first, so the catalogue write lands; the button then creates the override from `catalogueText` as rendered before the save (frontend/src/screens/CatalogueModule.tsx, CatalogueFields). Two writes for one intent, the wrong one first, and an override holding a stale value. Likely moot once the default flips (the task superseding ADR-178 points 1-3), but whichever act stays explicit has the same shape: a pending draft in a field must go where the button says, not where focus last was.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Pressing the explicit act while a field has unsaved typing sends that typing to the act's target only, and nothing to the other
<!-- AC:END -->
