---
id: TASK-105
title: >-
  There is no `.github/`, no linter, no type checking, no dependency or secret
  scanning.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: chore
ordinal: 205800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — a public reference implementation with no CI at all is a positioning problem before it is a quality one.** **There is no `.github/`, no linter, no type checking, no dependency or secret scanning.** The first thing a technical visitor does is look for the badge and the workflow file; their absence reads as "hobby" regardless of the 567 tests underneath, which is exactly the gap [[LAUNCH-GATES|Launch gate 1]] is about. **Do:** one workflow running the suite against a Postgres service container, plus Ruff, plus dependency vulnerability scanning and secret scanning. Type checking comes later and gradually — a strict `mypy` over this codebase today would produce a cleanup nobody asked for. **The rule for all of it: the checks inform review, they do not trigger an indiscriminate refactor.** A Vulture pass is worth running once by hand for the signal, not wiring into CI where it will cry wolf. Source: `CODE_QUALITY_RELEASE_POSITIONING_2026-09-19` §4 and §7.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 360, section "Features", position 58 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
