---
type: adr
status: accepted
topic:
  - architecture
  - api
  - security
  - deployment
created: 2026-10-02
modified: 2026-10-02
source:
  - "task-31 (unguarded /openapi.json, /docs and /redoc)"
  - "task-232 (Swagger Try-it-out cannot exercise an authenticated route)"
  - "Decided by the user 2026-10-02"
depends_on:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-151 — Authentication and Sessions]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
  - "[[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]"
  - "[[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]"
  - "[[ADR-173 — The Manager Client's Runtime Dependencies]]"
---

## Status
Accepted

## Context

[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] put a guard over the JSON plane, and [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] gave that guard a second credential type and a CSRF check. Both are wired the same way: the guard list `_api` in `backend/main.py` is attached to each router through `app.include_router(..., dependencies=_api)`. So the guard covers exactly what sits on a router.

**The API documentation does not sit on a router (verified 2026-10-02).** `/openapi.json`, `/docs` and `/redoc` are attached by FastAPI to the application itself, not to an `APIRouter`, so none of the `_api` dependencies apply to them. An anonymous caller can fetch the complete route inventory of a surface that `backend/main.py` presents as guarded: every path, every method, every request and response schema. No test covered it. That is the defect task-31 recorded. It is the same shape [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]'s `### Negative` warns about: a guard that reads as covering the plane while something on the plane sits outside it.

**Simply closing it would break two things the repository depends on.** [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 says the manager's API client is generated from the backend's OpenAPI schema and never hand-written. [[ADR-173 — The Manager Client's Runtime Dependencies]] point 2 turns that into a concrete fetch: `npm run generate:client` in `frontend/package.json` runs `openapi-typescript` against `http://127.0.0.1:8000/openapi.json`, and point 3's `npm run check:contract` regenerates from the same URL and fails on a diff. [[ADR-002 — API First Architecture]] makes the interface the boundary between components and counts "easier to test and document" among its gains. The strategy file's roadmap also lists FastAPI Swagger as part of the finished technical onboarding manual (`docs/playbook-strategy.md`). A published reference architecture probably wants its schema public. A deployment of it probably does not want `/docs` open to anyone who finds the host. Both of those are true at once, and they are true of different installations. That is why the answer is a setting and not a fixed rule.

**A second defect sat in the same place (task-232).** Even for someone entitled to call the API, Swagger's Try-it-out could not exercise any authenticated route. The generated document declared no security scheme, so Swagger UI showed no Authorize control. And Swagger UI does not send cookies unless `withCredentials` is set, so a person already signed in on the same origin still arrived at every guarded route as anonymous. The documentation described an API that its own console could not reach.

## Decision

**1. Exposure of the API documentation is one environment setting, `API_DOCS`, with three values.**

- `public`: `/openapi.json`, `/docs` and `/redoc` are all served to anyone. **This is the default for this local reference build.**
- `signed_in`: all three are served only behind the normal JSON guard. The caller needs either a session or a machine key that holds `view`, the same answer `enforce_api_policy` gives for any read on the plane.
- `off`: none of the three is served.

The three surfaces move together. There is no separate setting for the schema and the UIs.

**An unrecognised value stops startup.** It does not fall back to a default. The setting is documented in `backend/.env.example` as a deployment decision: turn it down before exposing an instance.

**2. The OpenAPI document declares the authentication that actually exists.**

It names two ways in, matching the two credential types `enforce_api_policy` accepts:

- a session cookie together with an `X-CSRF-Token` header, per [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]];
- a bearer key together with an `X-Brand` header, per [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]].

The public sign-in routes are marked as needing no credential. So are the provider webhooks, which the provider signs rather than authenticating with a platform-issued credential. The document describes the plane as it is, not as a single uniform scheme.

**3. Swagger UI is served with `withCredentials`.**

A browser already signed in on the same origin therefore sends its session cookie from Try-it-out. A machine key can be entered in Authorize. The session cookie is `httponly` and cannot be typed into Authorize, so for people the documented route is to sign in first and then use the console.

## Consequences

### Positive

- **The default no longer quietly contradicts itself.** Before this, `backend/main.py` described a guarded API while publishing its full inventory to anonymous callers, and nothing said so. The exposure is now a named, documented choice with a stated default.
- **Adopters get one explicit knob.** Going from reference build to deployment is one line in the environment, documented beside the other deployment settings in `backend/.env.example`. It is not a code change somebody has to find.
- **A typo cannot reopen the surface.** Because an unrecognised value stops startup, a misspelt `signed_in` or `off` fails loudly instead of publishing what it was meant to hide.
- **Try-it-out works.** A signed-in person can exercise guarded routes from `/docs`, and a machine integrator can paste a key into Authorize. The documentation becomes a working console for the plane it describes.
- **Codegen keeps working on the default.** `npm run generate:client` and `npm run check:contract` fetch `/openapi.json` anonymously, as [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 and [[ADR-173 — The Manager Client's Runtime Dependencies]] points 2 and 3 assume, with no change.

### Negative

- **The default is still open.** This is a deliberate choice for a reference build, not an oversight, but the cost is real: a careless deployment that skips the setting publishes the route inventory. The protection is documentation in `backend/.env.example`, not enforcement.
- **In `signed_in`, codegen needs credentials.** `generate:client` and `check:contract` fetch the schema anonymously from a fixed URL. Against an instance set to `signed_in` they get refused, so they must be given credentials or run against a local instance overridden to `public`.
- **Cookie-authenticated writes from Swagger also need the CSRF token pasted.** `withCredentials` sends the session cookie, but `enforce_api_csrf` still requires the `X-CSRF-Token` header on every write. A person using Try-it-out for a write must fetch the token from `GET /auth/session` and enter it. Reads need nothing extra.
- **The security declaration is a second description of the auth model, and it can drift.** If a third credential type or another unauthenticated route is added, the OpenAPI declaration must be updated with it, or the console will misdescribe the plane again in the way task-232 found.

## Notes

- **Not a supersession, and not an addendum.** No existing Decision is reversed. [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 still holds as written, and on the default it holds with no change at all. [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] and [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] are unchanged too: their guard is reused for `signed_in`, not altered. This record decides something none of them addressed, which is whether the description of the plane is itself on the plane.
- **The `signed_in` permission is `view`, the ordinary read permission.** The schema exposes the same route list that any `view`-holding caller can already discover by using the API, so asking for more than `view` would protect nothing the caller does not already have.
- **The test gap is part of the defect.** No test checked what an anonymous caller gets from `/openapi.json`, `/docs` or `/redoc`. That is why the gap outlived both guard records. Each of the three values needs a test for all three paths. Without one, this record repeats the problem [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]'s Notes describe for CSRF: a control that reads as in place over a surface nothing checks. **Closed with the implementation (2026-10-02):** `backend/tests/test_api_docs.py` checks all three paths in every mode, anonymous and with `view`. The non-default modes run in a fresh interpreter, because the setting is read when `main` is imported.
- **The default fits the POC stage, not production.** Installation and deployment are deliberately not started in this repository. When they are, the deployment guidance should treat `API_DOCS` as one of the settings to review before exposure, alongside `trust_proxy_headers` and the same-origin requirement in [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] point 3.

## Related ADRs

### Depends On
- [[ADR-002 — API First Architecture]]
- [[ADR-151 — Authentication and Sessions]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-173 — The Manager Client's Runtime Dependencies]]
