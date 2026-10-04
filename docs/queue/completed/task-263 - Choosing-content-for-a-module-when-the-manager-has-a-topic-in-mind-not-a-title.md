---
id: TASK-263
title: >-
  Choosing content for a module when the manager has a topic in mind, not a
  title
status: Done
assignee: []
created_date: '2026-10-03 18:56'
updated_date: '2026-10-04 10:22'
labels:
  - frontend
  - backend
  - needs-adr
dependencies: []
type: decision
ordinal: 300050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
User, 2026-10-03, after trying slice 6 (task-258): "when selecting content there should at least be some options to select (if a manager only has a general topic in mind, they might not have a specific title) -- this needs a separate session (because not sure how this is structured best)". The binding picker in frontend/src/screens/CatalogueModule.tsx (BindRecord) only searches GET /content/?q= by title. Raw material that exists: content categories (GET /content/categories; record assignments with scores), the facet work that is still open (task-207, ADR-175), recency, and the decision layer's candidate query (backend/app/decision/strategies/base.py:candidate_query). To be designed in its own session, likely an interview one question at a time, before code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A design session settles how a manager browses for content by topic, recorded in an ADR or the design pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Design session held 2026-10-04 with the user, one question at a time. Eight decisions:
1. A topic-only manager browses and chooses in the picker. A slot on one category already covers "the engine picks from this topic" and is unchanged.
2. Categories are the browse axis until facets exist. The picker reads them only and never creates or assigns one. Facets (task-207) join later as a second filter.
3. q matches title and description, in the picker and the Content list.
4. A category means direct assignment only, the same meaning candidate_query gives it, with no child expansion. The dropdown shows the hierarchy indented.
5. With a category, results are ordered by score descending, then newest. Text only: newest first. This is not the top_score tie-break, so the top row is not claimed to be the slot pick.
6. A row shows the title, a one-line description, and the fit, already-in-this-variant and not-published notices. None of them blocks binding. The score and the category list are not shown.
7. The picker opens listing records. It has a text field plus a one-category dropdown that combine, updates live after a short pause, and uses arrows, Enter and Esc.
8. The Content list gets the same category filter, built alongside task-267.
Recorded in: ADR-175 addendum 2026-10-04 (decisions 1-5); [[Campaign Write Surface - final design pass]], section "Choosing a record for a module" (all eight); playbook decision log 2026-10-04. Build tasks: task-268 (server), task-269 (picker), task-270 (Content list).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Settled how a manager finds content by topic: browse by category, read-only, until facets exist; title and description search; direct assignment, score order; a keyboard-driven picker that opens listing records. Verified by reading back the ADR-175 addendum (git diff shows additions only), the design-pass section and the three created build tasks.
<!-- SECTION:FINAL_SUMMARY:END -->
