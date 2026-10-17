---
id: TASK-394
title: The category graph's labels stay readable when categories crowd
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
updated_date: '2026-10-17 20:59'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 210800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-03; screenshot screenshots/20-graph.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. Audit P1: on Content, Graph, with the demo's 26 categories, labels sit under neighbouring circles and across the dense bundle of edges, so several category names are partly hidden. The table beside the graph says the same in words, so nothing is lost to a screen reader, but the drawing does not do its job. The graph is frontend/src/screens/CategoryGraph.tsx (the node classes at :135); it was never drawn in the design (HANDOFF section 9, decision 20) and opens full width since TASK-372 step 6. Its colours are TASK-392 item 1; this task is about legibility. The audit suggests: labels placed apart from the circles, fewer edges until a category is chosen, and a zoom or a view of one category's neighbours. Which of these is a design choice.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With the demo's categories every label in the graph is readable without overlapping a circle or another label
- [ ] #2 Choosing a category makes its relations stand out from the rest
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-17 evening, before this task: the graph was tidied for the November demo at the user's brief (commit after 504cf72): full width, small neutral dots, names only on hover or focus with the dot's links and neighbours lit and the rest faded, a chosen category's figures, relations and records in tables below, the full category list removed. So no label overlaps at rest; a crowded hover can still lay a name over a line. The redesign this task asks for (layout, zoom, a focused neighbourhood) is still open.
<!-- SECTION:NOTES:END -->
