---
id: TASK-286
title: >-
  The picker opens on records ready for the channel, and the Content list
  filters by readiness
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 19:19'
labels:
  - frontend
dependencies:
  - TASK-283
type: feature
ordinal: 200140
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-282 design session (2026-10-05): the picker and the Content list read readiness in the first build (the ADR-174 addendum 2026-10-05, point 3; Manager Workflow Q11 and Q5). Depends on the storage task (the `ready_for` filter and per-row `ready_for` on `GET /content/`).

**The bind picker** (`BindRecord` in `frontend/src/screens/CatalogueModule.tsx`, task-269):
- it opens on records ready for the variant's channel;
- a visible switch, "Show records not ready for <Channel>", widens the list;
- rows that are not ready carry a "Not ready for <Channel>" note (MW Q11: "an unready record appears marked as unready rather than absent");
- they can still be bound. A note informs and never blocks, as the other picker notes do.

**The Content list** (`frontend/src/screens/Content.tsx`) gets a "Ready for" filter (Any, Email, Push), held in the URL like status and category.

Tests; mutation-checked; a live check (read-only for the list, a scratch record for any bind).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The picker opens on records ready for the variant's channel, with a switch to show the rest marked "Not ready for <channel>"
- [x] #2 The Content list has a Ready for filter held in the URL
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: picker opens with ready_for=<variant channel>, a switch widens it, unready rows carry 'Not ready for <Channel>' and still bind; a push variant asks for push; text narrowing survives widening. Content list: Ready for filter from the URL (?ready=), channels from the field definitions, offset reset, Any drops it.
2. resources.ts: usePickerRecords and useContentList take readyFor -> ready_for.
3. CatalogueModule.tsx: channel passed to BindRecord (all three call sites); the widen switch; the note first among the notices.
4. Content.tsx: a 'Ready for' Choice held in the URL like status and category.
5. Mutation-check, client suite, tsc, contract; live check read-only, with scratch record 116 briefly activated to see the note.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Choices made in building: the Content list's channels come from the content field definitions (the record page's sections do the same), not a hard-coded Email/Push list, so a new channel appears without a code change; the field group with no channel is not offered. The 'Not ready for <Channel>' note is listed first among the picker's notes. The picker's widen switch is off each time the picker opens (component state, not remembered).
Test fixtures: the picker stub now honours ready_for; two older picker tests widen first (they bind Porto, the unready record) or count the ready rows; SlotSettings' content stub gained ready_for, which the real list always sends.
Validation: 5 new tests (plus 3 adjusted), failing first; 13 mutants — 12 caught after adding the push-variant test (the survivor 'always filters email' led to it); 1 was not a real mutant (an inert key prop). Client 180 passed, tsc clean, contract matches. Live: Content list ?ready=email lists 105 (this brand), ?ready=push none (nobody has marked push); picker on Demo Campaign 1's hero opens with ready_for=email (20 of 105), widening drops the filter; scratch 116, briefly active and unmarked, is absent by default and appears as 'task-279 live check · Not ready for Email' when widened. Nothing bound; 116 deactivated again, no marks, machine ready on.
Keyboard behaviour of the new switch is left for the keyboard-accessibility session (user, 2026-10-05).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The bind picker now opens on records ready for the variant's channel, with a 'Show records not ready for <Channel>' switch; unready rows are marked 'Not ready for <Channel>' and can still be bound. The Content list has a 'Ready for' filter held in the URL, offering the channels the field definitions name. Verified by 5 new tests, 12 caught mutants, 180 client tests, the contract check, and a live check (list counts; picker default and widened, with scratch record 116 shown as not ready), all restored.
<!-- SECTION:FINAL_SUMMARY:END -->
