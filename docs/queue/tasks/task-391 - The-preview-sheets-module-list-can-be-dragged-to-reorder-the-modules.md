---
id: TASK-391
title: The preview sheet's module list can be dragged to reorder the modules
status: To Do
assignee: []
created_date: '2026-10-17 10:34'
labels:
  - frontend
dependencies:
  - TASK-372
references:
  - docs/design/HANDOFF.md
type: feature
ordinal: 201107
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Raised by Diede in the design review of 2026-10-17: the preview shows the order of the modules on the left, which is good, and would be better if the list could be dragged to reorder them. Agreed; queued on its own, not part of TASK-372. The design draws the handle on that list only (docs/design/HANDOFF.md section 9, decision 24; render 24).

**It fits a recorded decision, and the module stack stays as it is.** The Variant Editor interview (docs/architecture/interview-prep/Variant Editor - design interview.md, Cluster 1 question 5, 2026-09-25) rejects drag-and-drop on the module stack, because a tall surface scrolls while you drag and that is where dragging fails; the code says the same (frontend/src/screens/VariantEditor.tsx: modules move with buttons and Alt+Arrow, never by dragging). The same record allows dragging on a compact outline of module and position that does not scroll, and calls that outline an addition to the screen cut. The preview sheet's module list is that outline. A first answer in the review proposed dragging on the stack; that was wrong, and it was corrected the same day.

**What to keep in mind.** Reordering from a preview changes saved state, so the sheet has to show the new order after a drop. The preview renders what is saved, and a save carries the version it was read at, so a conflict must be shown and never merged (task-110). The envelope module keeps position 0 (backend/app/campaigns/duplication.py), and positions are unique per variant, so any move is a renumber of the modules between the two positions; check whether the existing one-step move call can take any target position or whether a call that takes a position is needed. The up and down buttons, Alt+Arrow, and the stack's behaviour do not change. Where the outline lives (the sheet, or a panel of its own) is Diede's to confirm; the design assumes the sheet.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each row of the module list in the preview sheet has a drag handle, and dropping a row moves that module to that position and renumbers the modules between, with no gap
- [ ] #2 The envelope module cannot be moved, and nothing can be dropped before it
- [ ] #3 Reordering also works from the keyboard on the preview list, and the module stack in the editor gets no drag handle: its buttons and Alt+Arrow are unchanged
- [ ] #4 After a drop the sheet shows the email in the new order; a save over somebody else's newer edit is refused and shown, never merged
- [ ] #5 Tests cover a move up, a move down, a refused conflict and the envelope staying first
<!-- AC:END -->
