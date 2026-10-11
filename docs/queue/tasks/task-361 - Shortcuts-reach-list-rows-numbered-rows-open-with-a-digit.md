---
id: TASK-361
title: 'Shortcuts reach list rows: numbered rows open with a digit'
status: To Do
assignee: []
created_date: '2026-10-11 10:02'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 209900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Raised by the user on 2026-10-11: "g then c" reaches Campaigns, but nothing on the list itself is reachable by a shortcut, so a keyboard user still has to Tab or arrow into the table. The user's suggestion: number the rows, so after "g c" the keys 0-9 open the first ten rows.

**What exists.**
- Screen shortcuts: useShortcut in frontend/src/shortcuts/Shortcuts.tsx; the "Go to" keys come from SCREENS in frontend/src/shell/Nav.tsx. Hints show on their elements while Alt or Ctrl is held (Shortcuts.tsx:36-44).
- Lists are DataTable (frontend/src/components/DataTable.tsx), a React Aria grid with arrow-key navigation and onRowAction. Pages are 50 rows (PAGE_SIZE, frontend/src/components/Pager.tsx:5), not 10.

**Open for its final-design pass.**
- 1-9 and 0 for the first ten rows of the page, or a different scheme (the page holds 50); the hint shown on each numbered row while Alt/Ctrl is held.
- Conflicts: a digit typed into a search field must stay a digit (Shortcuts.tsx already ignores keys typed into fields; check).
- Paging by key (for example [ and ]) to reach rows beyond the first ten.
- One mechanism in DataTable, so every list gets it.

Keyboard accessibility as a whole is its own later session (agent memory: layout and keyboard come later); this is filed so the idea is kept.

**Related.** task-266 (the go-to shortcuts), task-362 (which key shows the hints).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On every list, a digit key opens the matching numbered row of the current page
- [ ] #2 The row numbers show as hints while the hint key is held
- [ ] #3 Digits typed into a field are never taken as shortcuts
<!-- AC:END -->
