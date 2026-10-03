---
id: TASK-262
title: >-
  "Overridden by X" on campaign detail is module-wide, so a catalogue edit to
  another field reads as an override
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:56'
updated_date: '2026-10-03 19:02'
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
- [x] #1 Campaign detail names which fields of a module are overridden, and a module with none says nothing about overrides
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. frontend/src/screens/CampaignDetail.tsx: the column is now 'Overridden here' and lists the overridden fields with their author ('headline_medium by sam'); a module without overridden fields shows a dash. Test fixture now carries a real overridden field; the old module-wide label as a mutant fails the test. 6 campaign-detail tests pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Campaign detail names which fields of a module are overridden instead of labelling the whole module, so a catalogue edit to another field no longer reads as an override. Verified by the updated test and a mutant restoring the old label.
<!-- SECTION:FINAL_SUMMARY:END -->
