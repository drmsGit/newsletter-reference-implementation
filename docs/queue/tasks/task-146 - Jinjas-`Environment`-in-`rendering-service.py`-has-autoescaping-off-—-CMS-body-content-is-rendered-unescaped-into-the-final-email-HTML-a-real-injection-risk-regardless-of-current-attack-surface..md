---
id: TASK-146
title: >-
  Jinja's `Environment()` in `rendering/service.py` has autoescaping off — CMS
  body content is rendered unescaped into the final email HTML, a real injection
  risk regardless of current attack surface.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 501000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** Jinja's `Environment()` in `rendering/service.py` has autoescaping off — CMS body content is rendered unescaped into the final email HTML, a real injection risk regardless of current attack surface. Fix: turn on autoescaping (`Environment(autoescape=True)`). Content should be escaped by default; rich formatting (bold, links) will be supported through a separate, controlled mechanism rather than allowing raw HTML injection through content fields — see the companion Feature logged for that. Security-adjacent, ranked high. Source: [[Interview Prep - Snapshots, Rendering, Email Modules]] → Rendering Q6. **Done 2026-07-12.**
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 521, section "Done", position 10 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
