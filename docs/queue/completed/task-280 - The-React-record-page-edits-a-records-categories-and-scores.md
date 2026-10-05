---
id: TASK-280
title: The React record page edits a record's categories and scores
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 18:25'
updated_date: '2026-10-05 11:38'
labels:
  - frontend
dependencies:
  - TASK-278
  - TASK-279
type: feature
ordinal: 200170
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-274 design session (2026-10-04, the user) and recorded in [[Content Write Surface - final design pass]] and the ADR-080 addendum of 2026-10-04. The Categories section of the React record page. Depends on task-278 (the in-place score route and the enforced 1–10 range).

- **List each assignment** with its category name and its score as a 1–10 choice, changed in place, which saves immediately through task-278's route. Data from `GET /content/{id}/assignments`.
- **Remove per row** (`DELETE /content/{id}/assignments/{aid}`).
- **Add** with the hierarchy dropdown the bind picker uses (`frontend/src/components/CategoryChoice.tsx`, task-269) plus a 1–10 score, through `POST /content/{id}/categories`. A duplicate answers 409 "Category already assigned"; show it, and don't offer categories already assigned.
- **One line under the heading:** "Categories build each recipient's interest profile. For finding content, facets will follow." This keeps findability labels out of the affinity vocabulary ([[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] and its 2026-10-04 addendum).
- **No creating categories here.** That stays in its own place.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Assignments are listed with an in-place 1-10 score, removable per row, and addable through the hierarchy dropdown
- [x] #2 The section states what categories are for and never offers to create one
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-05.
- Hooks: useContentAssignments, and useEditAssignments (assign, score via task-278's PATCH, remove; one mutation scope per record). It re-reads the assignments, the content list pages and the picker after every change, a refused one too, since a 409 means somebody assigned it meanwhile.
- CategoryChoice gains optional label, noneLabel and exclude props; the picker and Content list keep their defaults and their tests pass unchanged.
- Categories section on the record page:
  - the note "Categories build each recipient's interest profile. For finding content, facets will follow.";
  - each assignment with a 1-10 score Choice saved on change, and Remove;
  - Add through the hierarchy dropdown without the categories already assigned, plus a 1-10 score defaulting to 10;
  - no way to create a category.
- Errors show in the server's words, not through SaveState, which would call a 409 "somebody changed it" and shows nothing for a field error.
- Tests: 5 in ContentDetail.test.tsx, the stub server gaining categories and assignments. Mutation-checked against 7 mutants, each caught. Client tsc clean, vitest 158 passed.
- Checked live on scratch record 116: added Adventure at 10 (assignment 199), changed it to 3 in place (same assignment), removed it, and "No categories yet." showed.
- Polish noted, not done: each row shows the category name and then a visible "Score for <name>" label, which reads as a repeat. A visually hidden label would be tidier.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The record page edits a record's categories: each with an in-place 1-10 score, removable per row, addable from the hierarchy (already-assigned ones not offered), under a note saying what categories are for, with no way to create one. Verified by 5 tests mutation-checked against 7 mutants, the client suite (158) and a live add, re-score and remove on a scratch record.
<!-- SECTION:FINAL_SUMMARY:END -->
