---
id: TASK-368
title: AI drafts a content record from a source and proposes its categories
status: To Do
assignee: []
created_date: '2026-10-11 20:44'
updated_date: '2026-10-16 18:34'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11 as an extension of the AI subject suggestion: "create content and categorize". A manager gives a source (a text, a link's text, a short brief) and the AI drafts a content record's fields for the channels it is meant for, and proposes category assignments with scores. A person reviews and saves; nothing is published or assigned without them (ADR-080: the taxonomy is human-governed; ADR-140 Assistive mode).

**Design questions for its final-design pass.** Which fields it fills (fields.json concepts); whether the proposal uses existing categories only (ADR-080 suggests yes); how the proposal shows its reasons; the prompt and its budget (ADR-144). task-95 (AI taxonomy recommendations) is related but about the taxonomy itself, not one record.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-16 (task-100): the button that starts this model call is frontend/src/components/AIButton.tsx, which already waits visibly and asks once; do not hand-roll a pending state. The server-side guard against two runs at once is task-387.
<!-- SECTION:NOTES:END -->
