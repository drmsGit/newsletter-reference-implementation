---
id: TASK-398
title: 'Manager screens speak in labels, not internal names'
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 211200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-20; screenshot screenshots/74-slot-reasons.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. Decision slots show their Reasons given (frontend/src/screens/DecisionSlotDetail.tsx:106-110) as the engine writes them: category_ids, recipient_top_score and long floating-point formulas. Elsewhere manager screens show content_recommendation, list_unsubscribe, opted_in, headline_medium and an ADR number in a field's help. A manager has to translate these. The audit suggests human labels for strategies, categories and states, rounded scores, and the exact machine data kept behind a Technical details disclosure. Part of this is the backend's wording of reasons; the help texts with ADR numbers come from storage/fields.json notes, which are also read by the AI, so whether the AI and the person get different texts is part of the design.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Decision reasons name categories and strategies by their labels and show scores rounded
- [ ] #2 The exact machine form of a reason stays available behind a disclosure
- [ ] #3 No manager-facing help text shows an internal field name or an ADR number
<!-- AC:END -->
