---
id: TASK-393
title: 'Character shortcuts can be turned off, and pause while a dialog is open'
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 210700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-04 and UX-05; screenshot screenshots/54-shortcuts.jpg and 55-shortcuts-background-navigation.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. Two findings about the global shortcuts, one cause. (1) UX-04, audit P1, WCAG 2.1.4: the single-character shortcuts (?, /, p, and the g-then-letter sequences) work anywhere outside a text field, and there is no way to turn them off or move them to a modifier; the registry says so on purpose (frontend/src/shortcuts/Shortcuts.tsx:17, Not configurable this round). Speech input or a stray key can fire them. (2) UX-05, a defect: with the shortcut overview open on Settings, Brands and its Close button focused, g then c navigated the page behind the dialog to Campaigns while the dialog stayed open (the key handler, frontend/src/shortcuts/Shortcuts.tsx:76, does not look at whether a modal is open). The choice to make: an off switch (and where it lives: the overview itself, a user setting), or remapping to a modifier, or both; and whether a navigation shortcut inside a dialog is ignored or closes the dialog first. Neighbours: TASK-361 (digits open list rows, which adds more single-character keys and should follow whatever is decided here) and TASK-362 (which key shows the hints). The visible way into the overview and aria-keyshortcuts are TASK-392 item 19.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every single-character shortcut can be turned off by the user, and the choice persists
- [ ] #2 While a modal dialog is open, no shortcut acts on the page behind it
- [ ] #3 Keys inside focused widgets (lists, menus, text fields) keep working when the shortcuts are off
<!-- AC:END -->
