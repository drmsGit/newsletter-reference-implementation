---
id: TASK-49
title: the gaps that block the first React screen.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the gaps that block the first React screen.** **It said three and there were four.** **~~C1 the brand switcher~~ ✅ DONE 2026-09-20, ~~C15 the CSRF token after a reload~~ ✅ DONE 2026-09-20, C8 planning a send, C2 the settings surface** (`docs/react-screen-inventory.md`). C1 is one route and blocks the shell: `set_session_brand` has no JSON equivalent, so a cookie-authenticated SPA is stuck on whichever brand the session landed on. C8 is the largest capability gap in the product — `prepare_send_from_audience` has exactly one call site and it is the Jinja route, so without it "deliveries" is a read-only list of sends the client cannot create. C2 is not blocking the core loop and is blocking a usable product: there is no `app/settings/router.py` and no `app/ai/router.py`, so the entire settings surface is UI-only. **C15 was invisible to the method that found the others.** C1, C8 and C2 came from reading the API for what it cannot do; C15 came from walking the client's own lifecycle. Every route involved existed and worked — the CSRF token was obtainable only from the `/auth/session/verify` body, so a page reload left a valid session that could not write. `GET /auth/session` now returns it (dated addendum to ADR-168, three mutation-checked tests). **✅ The schema honesty pass is DONE 2026-09-20:** the four bare-dict routes (`process-due`, `process-expired`, `send-test`, `suggest-subject`) **plus the five session routes nobody had listed** — `/auth/session/request` and `/verify` also took `payload: dict = Body(...)`, so the generated client had no types at all for the sign-in flow. Twelve schemas added, none removed, path count unchanged. Two schema renames shipped with it: `RenderedVariant.html` → `artifact_body` (finishing ADR-162 pt 3) and `GET /email-modules` → `GET /modules`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 146, section "Features", position 2 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
