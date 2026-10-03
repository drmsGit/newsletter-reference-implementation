---
id: TASK-263
title: >-
  Choosing content for a module when the manager has a topic in mind, not a
  title
status: To Do
assignee: []
created_date: '2026-10-03 18:56'
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
- [ ] #1 A design session settles how a manager browses for content by topic, recorded in an ADR or the design pass
<!-- AC:END -->
