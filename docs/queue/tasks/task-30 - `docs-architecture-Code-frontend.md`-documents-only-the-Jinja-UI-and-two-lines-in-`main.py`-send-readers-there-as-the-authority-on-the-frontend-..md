---
id: TASK-30
title: >-
  `docs/architecture/Code/frontend.md` documents only the Jinja UI, and two
  lines in `main.py` send readers there as the authority on "the frontend".
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - docs
dependencies: []
priority: parked
type: docs
ordinal: 103000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟡 **[Docs] — `docs/architecture/Code/frontend.md` documents only the Jinja UI, and two lines in `main.py` send readers there as the authority on "the frontend".** That page (143 lines, written 2026-07-27) is a route index for `backend/app/frontend/router.py` and mentions React, Vite and the `frontend/` directory nowhere. `backend/main.py:190` and `:210` both point at it. Now that the SPA exists, a reader following those pointers gets a complete and confident answer about the wrong frontend — and the Jinja one has a deletion date. Needs either a second module page for the SPA or a split, plus corrected pointers. Source: React client Phase 1, 2026-09-20.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 96, section "Bugs", position 30 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
