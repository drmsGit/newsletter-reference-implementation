---
id: TASK-401
title: At phone width the editor shows one work area at a time
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 211500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-26; screenshot screenshots/63-phone-editor.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. At 390 by 844 the editor stacks the navigation (about 129 px), then the module list, then the editor, which starts around y=366; switching modules means scrolling past the other areas. The handoff asks for one column at a time at phone width. Today the narrow rule only collapses the navigation into a bar (frontend/src/index.css:534, below 800 px), and the splits have their own narrow rule (index.css:1272). The audit suggests a list-to-detail step with a clear Back, or a compact module picker. Responsive design is a later pass by decision (the layout comes after the build); this records the finding so that pass has it, and it may apply to every split, not only the editor.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 At phone width the editor shows either the module list or one module, with Back between them
- [ ] #2 The same holds for the other three-column screens, or the task says why not
<!-- AC:END -->
