---
id: TASK-258
title: 'The variant editor, catalogue fields and overrides (slice 6)'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:27'
updated_date: '2026-10-03 18:44'
labels:
  - frontend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200058
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Slice 6 of [[Campaign Write Surface - final design pass]], the client half, after its backend tasks. ADR-178 in the composer: a catalogue-bound module shows its record's fields, and typing edits the record (point 1); "Override here" converts one field, which then shows the catalogue value it covers (points 2, 4); reset per field, and per module with a confirmation (point 6); a passive count of unsent campaigns using the record, clickable to the list, no owner names (point 8, task-224); an optional reason as presets with free text behind Other (point 9; user 2026-10-03: "Shorter for this send", "Different tone for this audience", "Out of date for this campaign", "Legal or compliance", Other); no outcome_delta (point 10); none of it on a slot-bound module (point 5). Plus D5 (user 2026-10-03): "changed since last published — sends still use version N" with one-click Publish. And binding an unbound catalogue module to a record, by searching the content list.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A catalogue-bound module shows its record's fields; editing one saves to the record on blur with its version
- [x] #2 Override here converts one field; the covered catalogue value stays visible; typing saves the override with the module version
- [x] #3 Reset one field, and reset the module after a confirmation
- [x] #4 The unsent-campaign count is shown beside catalogue fields and opens the list
- [x] #5 An unpublished edit is said, with a Publish button
- [x] #6 An unbound catalogue module can be bound to a record found by title
- [x] #7 A reason can be given as a preset or Other text
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Hooks (resources.ts): useContentReach, useSaveCatalogueField (PATCH with the channel as group, record If-Match read at send time, own queue), usePublishRecord, useSetOverride (whole set built from the cached override at send time, module If-Match, module queue), useBindModule.
2. screens/CatalogueModule.tsx: catalogue fields edit the record; Override here per field; overridden field shows the catalogue value and Back to the catalogue value; reset all after a confirmation; reach count with the list on request; publish state with Publish; reason presets + Other; bind or rebind by title; slot-bound modules explained, never overridable.
3. Shared AutosaveField / SaveState / fieldError moved to components/EditorFields.tsx.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Tests: CatalogueModule.test.tsx (9) against a stub server enforcing both the record's and the module's version; the old catalogue-bound test in VariantEditor.test.tsx was superseded. Mutants: catalogue edit routed to the override, override dropping other fields, reset-all without asking, slot branch removed, publish state hidden, wrong field group, no record token, reach list shown unasked: each caught. 96 client tests, tsc clean. Browser on the dev backend (Demo Campaign 1 / Variant 1A, Hero Banner bound to record #101 'Edition 1 hero'): fields and 'used by 1 unsent campaign' shown, no publish warning (record matches its version); Override headline_hero here created the override with the catalogue value, the field showed 'overridden here' and 'Catalogue: Edition 1'; Back to the catalogue value reset it; both writes moved the module version, no conflict. Left behind: one inactive override row on module 1 and its audit entries (history, by design).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The variant editor now edits catalogue-bound modules as ADR-178 decides: fields edit the record by default, Override here converts one field and keeps the catalogue value in view, reset per field and per module (confirmed), the unsent-campaign reach and the publish state with one-click Publish beside them, reason presets, and binding by title. Verified by 9 tests against a version-checking stub, eight mutants caught, and a live override round trip.
<!-- SECTION:FINAL_SUMMARY:END -->
