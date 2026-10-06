---
id: TASK-291
title: The variant editor hides and shows a module's fields
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 21:27'
updated_date: '2026-10-06 11:15'
labels:
  - frontend
dependencies:
  - TASK-290
type: feature
ordinal: 200378
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-218 design interview (2026-10-05, with the user); recorded in [[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]] and [[Element Hiding - final design pass]], decisions 3 and 7. Third of three build tasks; depends on the module's hidden fields.

**Build** in the React variant editor (`frontend/src/screens/CatalogueModule.tsx`, the module's fields):
- a **Hide** toggle on each field the module's manifest marks hideable (`hideable` from `GET /modules`), writing through `PUT /campaigns/modules/{id}/hidden-fields` with the module's version, in the composer's write queue;
- a hidden field **folds to its label with "Hidden in this module"** and no input; showing it again brings the stored value back (nothing was cleared);
- the bind picker's **"Lacks X for this module"** note skips fields the module hides;
- the preview needs nothing new: the server renders without the hidden field.

Refusals show in place (403, 409 with "Load their version", 422 naming the field). Keyboard behaviour of the toggle is left for the keyboard-accessibility session (user, 2026-10-05); layout for the layout session.

Tests per screen convention with a stub server, mutation-checked; a live check on a scratch campaign only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each hideable field has a Hide toggle that saves through the route with the module's version
- [x] #2 A hidden field folds to its label; showing it restores the stored value
- [x] #3 The picker's Lacks note skips hidden fields
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in CatalogueModule.test.tsx: a switch on each hideable field and none on a field that is not; hiding with the module version, folding, showing again with the stored value; the whole list in manifest order; the group on a slot-filled module; the picker's Lacks note skipping a hidden field; a 422 at the field; a 409 with Load their version.
2. resources.ts: useSetHiddenFields, in the composer's module write queue.
3. CatalogueModule.tsx: useHide (one mutation per module), HideSwitch, HiddenField (folded), HiddenFieldsGroup for slot-filled and unbound modules; the picker's required list less the module's hidden fields.
4. Mutation-check, suites, live check on scratch campaign 7.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Choices within the design: where a module's fields are listed (bound to a record) the switch sits under each hideable field and a hidden field folds to its label with "Hidden in this module" — no input and no "Change in catalogue"; where they are not (slot-filled, or not bound yet) a group "Fields shown in this module" holds the switches, since the choice is the module's whatever fills it. The switch is read-only while saving (keeps focus, as on the record page). The list is sent whole, in the manifest's order. Static modules (cms: false) get nothing: none marks a field hideable. Keyboard behaviour left for the keyboard-accessibility session.
Validation: 7 new tests, failing first; 11 mutants caught (the survivor 'switch on every field' led to a non-hideable content field in the stub and an assertion it gets none). Client 189, tsc, contract unchanged. Live on scratch campaign 7 (variant 13, module 43): the four switches show with Body checked and folded; showing Body brought its stored text back and the preview has it; hiding the required Headline folded it, dropped it from the preview and left missing_required empty; shown again — the module ends with nothing hidden.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The variant editor now hides and shows a module's fields (ADR-187): a "Hide <field> in this module" switch on each field the manifest marks hideable, a hidden field folded to its label with "Hidden in this module", and a group of the same switches on slot-filled and unbound modules. Writes go through the module's version; refusals show at the field or with Load their version; the picker's "Lacks" note skips hidden fields. Verified by 7 tests, 11 caught mutants, 189 client tests and a live check on scratch campaign 7, left with nothing hidden.
<!-- SECTION:FINAL_SUMMARY:END -->
