---
id: TASK-232
title: >-
  The API docs cannot authenticate, so no protected route can be tried from
  /docs
status: To Do
assignee: []
created_date: '2026-09-28 20:32'
updated_date: '2026-09-28 20:32'
labels:
  - backend
  - docs
dependencies: []
type: bug
ordinal: 303200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Swagger UI at `/docs` cannot exercise any authenticated endpoint. Every protected route answers `401 Authentication required` from Try-it-out, so the interactive documentation demonstrates only the handful of public routes — on a project whose second pillar is an explorable API.

**Two causes, and neither is the cookie being wrong.**

**(1) No security scheme is declared.** `FastAPI(...)` (`backend/main.py:214`) passes `title`, `version`, `description` and `openapi_tags` and nothing else, and a grep for `APIKeyCookie`, `OAuth2` or any security scheme across `backend/` returns nothing. The generated OpenAPI document does not say the API is authenticated at all, so Swagger UI shows no **Authorize** control — there is nowhere to put a credential even if you have one.

**(2) Try-it-out does not send cookies.** Swagger UI issues requests without credentials unless the app sets `swagger_ui_parameters={"withCredentials": True}`, which `main.py` does not. So even a browser already signed in at `/manager`, holding a valid `nra_session` on the same origin, sends nothing from `/docs`.

**Why it costs more here than on a normal project.** The playbook sells an explorable API — [[ADR-002 — API First Architecture]] — and `docs/implementation/FastAPI.md` names automatic documentation as a reason the framework was chosen: *allows developers to explore and test APIs without manually creating documentation*. A visitor who opens `/docs`, presses Try-it-out and gets 401 on everything concludes the API does not work. That is a positioning cost, not only a convenience one.

**The two fixes are not alternatives.** An `APIKeyCookie(name="nra_session")` scheme documents the truth and gives Swagger an Authorize box; `withCredentials` makes the request actually carry the cookie. **Check what the scheme does to the generated client before shipping it** — the OpenAPI document is the input to `openapi-typescript`, so adding security to every operation changes what is generated, and that is the kind of change the TypeScript-pin item warns can pass `tsc` while breaking generation.

**A third option worth weighing rather than assuming:** an httponly cookie cannot be pasted into an Authorize box by hand, which is the usual reason this stays broken. A dev-only bearer, or a documented sign-in-first flow, may be the honest answer.

Found 2026-09-28 by the user while trying to exercise `GET /content/fields`, which had just been built and could not be tried.
<!-- SECTION:DESCRIPTION:END -->
