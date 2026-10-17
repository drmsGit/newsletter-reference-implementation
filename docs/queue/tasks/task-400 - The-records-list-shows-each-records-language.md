---
id: TASK-400
title: The records list shows each record's language
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 211400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-27; screenshot screenshots/14-records.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. On Content, Records the demo's English translations and German originals are interleaved, and a row shows title, description and state but no language; the filters are Status, Category and Ready for. Records have had a language since ADR-200 (frontend/src/api/resources.ts:1304, and translation into a brand's other languages, :1368). A short language cue on each row, marking an original and its translations, helps a manager pick the right one for a channel. A language filter could follow once the intended catalogue workflow is settled.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each row in the records list shows the record's language
- [ ] #2 A translation can be told apart from its original in the list
<!-- AC:END -->
