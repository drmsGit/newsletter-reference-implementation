---
id: TASK-362
title: 'Decide which key shows the shortcut hints: Alt, Ctrl, or both'
status: To Do
assignee: []
created_date: '2026-10-11 10:02'
labels:
  - frontend
dependencies: []
type: decision
ordinal: 210000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Decision]** Raised by the user on 2026-10-11: shortcut hints show while Alt **or** Ctrl is held on its own, and the user asked why both. No record says: the code accepts either (HINT_KEYS in frontend/src/shortcuts/Shortcuts.tsx:42-44, "Alt (Option on a Mac) or Ctrl, held alone"), added in 8ba8858 on 2026-10-04 when the hints were asked for, with no reason given.

**Likely reasons, to confirm or drop.**
- Platforms differ: Option on a Mac types special characters in combination, Alt on Windows and Linux focuses the browser's menu bar in some browsers, so one key may misbehave on one platform.
- Held **alone** is what makes either safe today: any other key, letting go, or leaving the window hides the hints again (Shortcuts.tsx around :103).

**To decide.** One key, or both; if one, which, per platform or for all. A small UI decision: record it in this task (and in the shortcut code's comment), not an ADR, unless it changes ADR-level keyboard rules.

**Related.** task-361 (numbered rows, which would show their numbers with the same key), task-266.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The hint key is decided, with its reason, and the code's comment says why
<!-- AC:END -->
