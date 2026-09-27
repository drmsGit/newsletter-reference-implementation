---
id: TASK-31
title: '`/openapi.json`, `/docs` and `/redoc` are reachable with no credential at all.'
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: parked
type: decision
ordinal: 103100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟡 **[Needs ADR] — `/openapi.json`, `/docs` and `/redoc` are reachable with no credential at all.** Verified 2026-09-20. `docs_url`/`openapi_url`/`redoc_url` are not customised in `backend/main.py`, and FastAPI attaches those routes to the **app** rather than to an `APIRouter` — so none of the `include_router(..., dependencies=_api)` guards apply to them and the policy table is never consulted. An anonymous caller gets the complete route inventory of a surface `main.py` describes as "guarded since 2026-09-18 (ADR-166, launch gate 3)". **No test covers this**, in either direction. **The tension that makes it an ADR rather than a bug:** [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 generates the typed client from this endpoint, and [[ADR-002 — API First Architecture]] wants the contract legible — so "lock it down" is not free, and the honest question is whether a published reference architecture *wants* its schema public. Probably yes for the schema and no for `/docs` in a deployment, which is a configuration decision an adopter should be handed rather than one this repo takes silently. Source: React client planning session, 2026-09-20.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 98, section "Bugs", position 31 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
