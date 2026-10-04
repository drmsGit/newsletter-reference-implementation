---
id: TASK-266
title: 'A keyboard shortcuts overview, and the shortcuts it lists'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 09:14'
updated_date: '2026-10-04 09:17'
labels:
  - frontend
dependencies: []
documentation:
  - docs/architecture/interview-prep/Variant Editor - design interview.md
type: feature
ordinal: 200065
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Variant Editor interview, "Established during Cluster 1 — the client is keyboard-first" (2026-09-25): a product-level requirement for every screen ("high focus on keys and shortcuts (resend has a great shortcuts overlay)"), and "a shortcuts overlay is part of the deliverable" — without one, shortcuts exist for whoever reads the documentation, which is nobody. Left for the build: which keys, global or per-screen, configurable or not. Taken 2026-10-04 without interrupting the user (they asked not to be interrupted in the building flow), recorded here: ? opens the overview anywhere, Esc closes; global two-key "go to" pairs (g a approvals, g c campaigns, g m monitoring, g t content, g u audiences, g d deliveries, g s decision slots, g , settings); per screen / focuses a list search, p opens the editor preview, Alt+Up/Down move a module (built in slice 5, now listed); not user-configurable this round; never fired while typing in a field; one registry the overview reads, so it cannot drift from the keys.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ? opens an overview listing the global shortcuts and those of the current screen; Esc closes it
- [x] #2 g followed by a letter goes to that screen
- [x] #3 / focuses the search on a list screen, p opens the preview in the variant editor
- [x] #4 No shortcut fires while typing in a field
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/shortcuts/: ShortcutsProvider (one keydown listener, two-key sequences with a short timeout, typing guard), useShortcut(keys, description, handler | null, group) registering into it; documentation-only entries for keys handled elsewhere (Alt+Arrow).
2. ShortcutsOverlay (React Aria Modal) listing registrations by group.
3. Shell: ? and the g pairs; SearchBox: /; PreviewBar: p; Stack: Alt+Arrow listed.
4. Tests, mutants, live check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-04. Built: src/shortcuts/Shortcuts.tsx (ShortcutsProvider with one keydown listener, two-key sequences within a second, a typing guard for inputs, textareas, selects and contenteditable, and modifier keys left alone; useShortcut registering while mounted, a no-op without a provider; the overview as a React Aria modal grouped Global / Go to / This screen). Go-to keys declared beside each link in Nav's SCREENS, so the menu and the keys come from one list. / registered by SearchBox (every list search), p by the preview bar, Alt+Up/Down listed from the module stack (handled there since slice 5). Tests Shortcuts.test.tsx (6) and Preview.test.tsx (+1); mutants: fires while typing, no sequence timeout, never unregisters, no p: each caught. 123 client tests. Live: ? listed all three groups on the editor, g c went to /manager/campaigns, / focused the campaign search.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The client has its keyboard shortcuts and the overview that lists them: ? anywhere, g-then-letter to every screen, / for a list's search, p for the editor preview, Alt+arrows listed, never fired while typing; the overview reads the same registry the keys run from. Verified by 7 tests, four mutants, and a live check.
<!-- SECTION:FINAL_SUMMARY:END -->
