---
id: TASK-281
title: A content record can be created from the React Content list
status: To Do
assignee: []
created_date: '2026-10-04 18:25'
updated_date: '2026-10-04 18:25'
labels:
  - frontend
dependencies:
  - TASK-279
type: feature
ordinal: 200180
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-274 design session (2026-10-04, the user) and recorded in [[Content Write Surface - final design pass]]. Creating a content record in the React client.

"New record" on the Content list (`frontend/src/screens/Content.tsx`) opens a small dialog with Title (required) and Description (optional). It posts `POST /content/` with empty `content` and lands on the new record's page (task-279's record page), where the fields autosave like any edit. Nothing else is required: [[ADR-177 — A Field Is Defined Once, Required Per Module]] point 4, nothing is required at catalogue level. So the Jinja create form's required `headline_medium` (`backend/app/frontend/router.py:2136`) is not carried over. One way to fill fields, not two.

The keyboard-first rule applies (the Variant Editor interview): the dialog opens from a shortcut listed in the `?` overview, submits on Enter, and closes on Esc.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A dialog asks for a title (required) and a description, creates the record and lands on its page
- [ ] #2 It is reachable and submittable from the keyboard, and listed in the shortcut overview
<!-- AC:END -->
