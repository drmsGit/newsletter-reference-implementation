---
id: TASK-281
title: A content record can be created from the React Content list
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 18:25'
updated_date: '2026-10-05 11:45'
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
- [x] #1 A dialog asks for a title (required) and a description, creates the record and lands on its page
- [x] #2 It is reachable and submittable from the keyboard, and listed in the shortcut overview
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-05.
- useCreateContent posts POST /content/ with {title, description or null, content: {}}.
- screens/ContentCreate.tsx: a "New record" button and the n shortcut (listed in the ? overview) open a React Aria Modal dialog asking for Title (required, focused) and Description. Enter submits, Esc closes. On success it opens the new record's page, where fields autosave (task-279). A refusal shows in place and the dialog stays open.
- Tests: screens/Content.test.tsx (4). Mutation-checked against 8 mutants, each caught. Client tsc clean, vitest 162 passed.
- Checked live in the React client: on the Content list, n opened the dialog with focus in Title; typing "task-281 live check" and Enter created record 117 and opened its page. It was then deactivated, like scratch record 116.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A content record can be created from the React Content list: a dialog (button or n) asks for a title and a description, creates the record and opens its page, where the fields autosave. Verified by 4 tests mutation-checked against 8 mutants, the client suite (162) and a live create through the keyboard.
<!-- SECTION:FINAL_SUMMARY:END -->
