---
id: TASK-30
title: >-
  `docs/architecture/Code/frontend.md` documents only the Jinja UI, and two
  lines in `main.py` send readers there as the authority on "the frontend".
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-04 17:55'
labels:
  - docs
dependencies: []
priority: p3
type: docs
ordinal: 103000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟡 **[Docs] — `docs/architecture/Code/frontend.md` documents only the Jinja UI, and two lines in `main.py` send readers there as the authority on "the frontend".** That page (143 lines, written 2026-07-27) is a route index for `backend/app/frontend/router.py` and mentions React, Vite and the `frontend/` directory nowhere. `backend/main.py:190` and `:210` both point at it. Now that the SPA exists, a reader following those pointers gets a complete and confident answer about the wrong frontend — and the Jinja one has a deletion date. Needs either a second module page for the SPA or a split, plus corrected pointers. Source: React client Phase 1, 2026-09-20.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The React manager client has its own code-module page, and frontend.md says it covers the Jinja UI only
- [x] #2 The two pointers in backend/main.py name both pages, so a reader is not sent to the wrong frontend
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 96, section "Bugs", position 30 in that section (top = do next). The description is the original entry, verbatim.

Done 2026-10-04.
- Verified the entry was still true: frontend.md described only backend/app/frontend (Jinja), and main.py:195 and :213 pointed at it as "the frontend".
- New docs/architecture/Code/manager-client.md, built from an Explore sweep of frontend/: purpose, key files, how it talks to the API (generated types, read(), If-Match writes, session/CSRF), conventions (React Aria, URL-held paging and filters, save on blur, shortcut registry), running and testing, invariants, change-impact. No live counts.
- frontend.md: a note at the top that it is the Jinja UI, that it still owns / (hence /manager), and that vite.config.ts records the base path becoming / when backend/app/frontend/router.py is deleted. The route table is untouched.
- MOC: manager-client listed beside frontend in both places.
- main.py: the API description and the frontend tag name both pages. Text only.
- All wikilinks resolve. Full backend suite 1248 passed. The tag text was checked from app.openapi() because the preview servers had been stopped by the app.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The React manager client has its own code-module page (manager-client.md). frontend.md says it is the older Jinja UI and links there, and the Swagger pointers in main.py name both, so nobody is sent to the wrong frontend. Verified links resolve, the tag text via app.openapi(), and the full backend suite (1248).
<!-- SECTION:FINAL_SUMMARY:END -->
