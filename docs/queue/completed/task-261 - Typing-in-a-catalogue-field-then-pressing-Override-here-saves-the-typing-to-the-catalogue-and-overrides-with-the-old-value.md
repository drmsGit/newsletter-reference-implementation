---
id: TASK-261
title: >-
  Typing in a catalogue field, then pressing Override here, saves the typing to
  the catalogue and overrides with the old value
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:56'
updated_date: '2026-10-03 19:09'
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
- [x] #1 Pressing the explicit act while a field has unsaved typing sends that typing to the act's target only, and nothing to the other
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Fixed with task-260: AutosaveField takes onLeave(draft, next) and the field hands typing to its own 'Change in catalogue' act instead of saving it as an override (no write at all until 'Save to the catalogue'); the two field states are keyed apart so the opening press cannot land on Save. Test: 'takes typing meant for the catalogue there, without overriding on the way (task-261)'; mutants removing the hand-off or the keys each fail it.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Typing left for the field's own catalogue act now goes to that act only: nothing is written until it is saved there. Verified by a dedicated test and two mutants.
<!-- SECTION:FINAL_SUMMARY:END -->
