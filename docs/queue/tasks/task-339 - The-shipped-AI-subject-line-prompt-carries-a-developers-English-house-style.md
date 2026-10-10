---
id: TASK-339
title: The shipped AI subject-line prompt carries a developer's English house style
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 18:43'
updated_date: '2026-10-10 20:41'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200770
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The one worked example of "the manager owns the prompt" (ADR-140, ADR-141) ships a developer-written editorial style: backend/app/ai/tasks/subject_preheader.py:40-61, DEFAULT_PROMPT. It is in English, and its rules are matters of taste: "No exclamation marks, no 'Discover', no emoji", "Be concrete". It also says "email newsletter". The first thing a manager sees when they open the prompt is someone else's house style, in the wrong language for the German buyer. Business baseline finding P2-H1.

Decided by the user in the 2026-10-09 interview review. The shipped seed keeps only:
- what the code needs, which is the three-option SUBJECT/PREHEADER format the reply is parsed in;
- the technical limits (subject at most 60 characters, preheader at most 90).

The taste rules go. In their place is a clearly marked line for the manager's own house style. The prompt tells the model to write in the language of the content, so a German newsletter gets German suggestions without German being hardcoded.

Final-design pass: check how the default reaches an installation. If it is seeded as a published prompt version, changing the constant affects only new installations; say what happens to an existing version.

Source: docs/business-interview-baseline.md → P2-H1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The shipped default prompt contains no editorial taste rules, only the parsed format and the 60/90 limits
- [ ] #2 It has a marked place for the manager's own house style
- [ ] #3 It asks for suggestions in the language of the content
- [ ] #4 The reply is still parsed as before
<!-- AC:END -->
