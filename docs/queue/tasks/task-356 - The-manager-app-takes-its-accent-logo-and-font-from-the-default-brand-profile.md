---
id: TASK-356
title: The manager app shows the working brand's logo from its default brand profile
status: To Do
assignee: []
created_date: '2026-10-11 08:39'
updated_date: '2026-10-11 08:42'
labels:
  - frontend
  - backend
dependencies:
  - TASK-350
type: feature
ordinal: 200990
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 5 of 5 of the brand-profile design (ADR-194, 2026-10-11).

The manager app shows the working brand's logo, taken from that brand's default profile, so a manager sees which brand they are working in.

**Only the logo.** The user first decided (question 6) that accent colour, logo and font would come from the default profile, with a contrast guard. After reading the design draft (docs/design/DESIGN.md: 'the manager app is one palette per install, not per brand'), the user narrowed it the same day to the logo only, so that:
- the app keeps one palette and its IBM Plex Sans and Mono fonts per installation;
- the design's colour meanings hold (teal marks what the system chose, ochre what a person pinned);
- a brand accent cannot clash with them.

This replaces task-94's separate web palette idea for the app.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The app shows the working brand's logo from its default profile, and switching brand switches it
- [ ] #2 The app's palette and fonts do not change with the brand
<!-- AC:END -->
