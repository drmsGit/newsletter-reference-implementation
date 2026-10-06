---
id: TASK-298
title: Engagement in the audience editor
status: To Do
assignee: []
created_date: '2026-10-06 19:59'
updated_date: '2026-10-06 21:21'
labels:
  - frontend
dependencies:
  - TASK-296
  - TASK-297
  - TASK-300
type: feature
ordinal: 200391
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-293 interview (2026-10-06, with the user); [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]] points 4 and 5. Fourth of four build tasks; depends on builds 2 and 3.

**Build** in the rule editor of build 3: an engagement field — what (received, opened, clicked), which mailing (a send chosen from the brand's sends, a campaign, or any send), when (between two dates, within the last N days, more than N days ago) — and the "did not" hint shown where an engagement field is used in "Who's in" ("To reach people who did not click, include who received it and leave out who clicked").

Tests per screen convention, mutation-checked; a live check on a scratch audience.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A rule can be given an engagement field (what, which mailing, when) in the editor
- [ ] #2 The did-not hint is shown
<!-- AC:END -->
