---
id: TASK-370
title: AI prepares a variant from a topic
status: To Do
assignee: []
created_date: '2026-10-11 20:44'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11: "prepare variant based on topic". A manager names a topic and the AI proposes a variant: which content records to bind or which categories a slot should draw from, plus a subject and preheader. A person reviews before anything is saved (ADR-140 Assistive mode).

**Design questions for its final-design pass.** Whether it proposes hand-bound records, slot configuration, or both; how it uses the catalogue (only ready, published records, as `candidate_query` does); what it writes and how the proposal is shown; budget (ADR-144). Builds on the subject suggestion in React and on realistic demo content (task-71).
<!-- SECTION:DESCRIPTION:END -->
