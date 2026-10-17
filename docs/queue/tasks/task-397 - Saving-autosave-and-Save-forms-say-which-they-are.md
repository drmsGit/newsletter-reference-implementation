---
id: TASK-397
title: 'Saving: autosave and Save forms say which they are'
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 211100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-14 and UX-15; screenshot screenshots/68-profile-footer.jpg and 15-record-detail.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. Two save models live side by side and neither says which it is. Records save a field when it loses focus (AutosaveField, frontend/src/components/EditorFields.tsx:82-87), with no cue at rest that this happens. Brand profiles and personalisation entries have a Save button (frontend/src/screens/Personalisation.tsx:273), and the entry's Save is enabled before anything has been changed. On a long profile (Newsletter Deutsch: legal details, look, header, footer) the only Save is a card at the bottom that scrolls out of view (UX-14). A manager can wait for Save on a page that already saved, or leave a profile thinking an edit persisted. To decide: one cue for autosaved pages (for example: Saves when you leave a field, with a saved state), and for Save forms a dirty state with Save disabled until something changed, kept in view on long forms, or a save per section. The audit is explicit that no save failed; this is about clarity.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A page that autosaves says so at rest, and shows when a change has been saved
- [ ] #2 A Save button is enabled only when there is a change to save
- [ ] #3 On a long Save form the Save action stays reachable without scrolling to the end
<!-- AC:END -->
