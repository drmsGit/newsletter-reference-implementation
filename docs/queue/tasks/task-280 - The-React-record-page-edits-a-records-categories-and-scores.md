---
id: TASK-280
title: The React record page edits a record's categories and scores
status: To Do
assignee: []
created_date: '2026-10-04 18:25'
updated_date: '2026-10-04 18:25'
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
- [ ] #1 Assignments are listed with an in-place 1-10 score, removable per row, and addable through the hierarchy dropdown
- [ ] #2 The section states what categories are for and never offers to create one
<!-- AC:END -->
