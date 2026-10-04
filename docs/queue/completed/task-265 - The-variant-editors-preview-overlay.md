---
id: TASK-265
title: The variant editor's preview overlay
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 07:29'
updated_date: '2026-10-04 07:34'
labels:
  - frontend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200063
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Started 2026-10-04 at the user's request, after the seven slices. Variant Editor interview 2.1: a collapsed preview bar that opens the full render as an overlay; checking it must be fast, never switch screens, ideally need no render button — which autosave (design pass D1) makes possible, since the render reads saved state. 4.1: the author sees a live render (the approver sees the snapshot). 4.2: an optional named recipient; read-only, and says so when it shows the generic pick. 4.3: a preview is a sketch showing unpublished edits; a test send shows what will ship. 4.4: three slot states, only "finds nothing" marked. The backend half is task-227 (module states on the render response).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A preview bar on the editor summarises what the render found, refreshed after each save
- [x] #2 The overlay shows the rendered email (sandboxed) or the push fields, without leaving the editor
- [x] #3 Module states are listed, with finds-nothing marked and the other two plain
- [x] #4 A recipient can be named; a generic fallback is said
- [x] #5 The overlay says a preview shows unpublished edits and a test send shows what ships
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Hooks: useRenderedVariant(variantId, recipientId, stamp) keyed by the composition's update time so it re-renders after every save; useRecipientSearch(q).
2. screens/Preview.tsx: PreviewBar (findings summary + Open preview) and the overlay (React Aria ModalOverlay/Modal/Dialog): note, recipient search, module states, iframe srcDoc with sandbox for email, a field list for push.
3. Wired into VariantEditor above the stack; tests; mutants; live check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-04. Built: useRenderedVariant keyed by the composition's update time (every save re-renders) and useRecipientSearch; screens/Preview.tsx with the bar (findings summary; 'could not be rendered' on failure, never a false all-clear) and the overlay (React Aria ModalOverlay/Modal/Dialog): the 4.3 note, recipient search, module states with only finds-nothing marked, the email in an iframe with sandbox="" and srcDoc, a push as its fields. Tests Preview.test.tsx (6); mutants: no re-render after save, no sandbox, finds-nothing unmarked, generic said with nobody named, failure read as all-clear, recipient not sent: each caught. 110 client tests, 1195 backend. Live (Variant 1A): bar 'Nothing to flag.'; overlay rendered the email; Image Left first read 'not run yet' although slot #1 had picked 40 times per recipient, which led to the per_recipient state (task-227 note); named noah.36@example.com showed his own pick, 'Winter feature #4', matching the slot's history.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The variant editor has its preview: a bar that says what the render found, refreshed after every save, and an overlay with the sandboxed render, module states (finds-nothing marked), an optional named recipient with the generic fallback said, and the note that a test send is what ships. Verified by 6 client tests and six mutants, a backend refinement found live, and a live check showing a named recipient's own pick.
<!-- SECTION:FINAL_SUMMARY:END -->
