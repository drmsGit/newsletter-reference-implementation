---
id: TASK-291
title: The variant editor hides and shows a module's fields
status: To Do
assignee: []
created_date: '2026-10-05 21:27'
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
- [ ] #1 Each hideable field has a Hide toggle that saves through the route with the module's version
- [ ] #2 A hidden field folds to its label; showing it restores the stored value
- [ ] #3 The picker's Lacks note skips hidden fields
<!-- AC:END -->
