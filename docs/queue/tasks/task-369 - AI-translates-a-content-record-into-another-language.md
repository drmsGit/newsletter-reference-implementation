---
id: TASK-369
title: AI translates a content record into another language
status: To Do
assignee: []
created_date: '2026-10-11 20:44'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11: "translate content". A manager asks for a content record in another language; the AI drafts the translated fields and a person reviews them.

**Design questions for its final-design pass.** Where a translation lives: a new record linked to the original, or a language version of the same record — recipients have a language, brand profiles exist once per language (ADR-194 point 6), and nothing models a record's language today. Which fields are translated (text, rich text; never URLs). How a translation stays honest when the original changes. Budget and prompt (ADR-144).
<!-- SECTION:DESCRIPTION:END -->
