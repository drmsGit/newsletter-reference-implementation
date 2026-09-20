---
type: adr
status: accepted
topic:
  - architecture
  - frontend
created: 2026-09-19
source:
  - "BETA-SCOPE §5, resolved 2026-08-22; recorded as an ADR 2026-09-19"
depends_on:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-131 — Email Module Templates Use MJML as Source Format]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
  - "[[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]"
---

## Status
Accepted

## Context

The framework choice was made on 2026-08-22 and has lived since then in a business document. `docs/business/BETA-SCOPE.md` §5 says so itself: *"Framework choice is a technical/architecture call, not a business one — per this repo's own rule … it should get a short ADR … rather than living only in this business doc."* This record is that, written before the scaffold rather than after it.

**The reflex answer was Next.js, and it was challenged and rejected.** Next.js earns its keep on SSR, SEO and content-heavy public pages. The manager client has none of those: it serves no anonymous traffic, needs no SEO, and its entire job is talking to an existing REST API from behind a login. An app-router instance's server-component and edge machinery would go mostly unused in an admin panel, and the learning surface would be paid in full anyway.

The "one app or two?" fork that would have complicated this was closed the same day. The anonymous-facing, SEO-relevant site — the official website go-live, where a Next.js-shaped tool *would* earn its keep — is real and belongs to a later Phase 4 effort, not to beta. Phase 4C was always scoped as "website and/or ebook", so beta's own publishing does not need it either. **One app is in scope; the second is not being built in any framework yet.**

**One argument arrived after the decision and strengthens it.** [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] point 3, taken on 2026-09-19, makes FastAPI serve the built client and same-origin a stated deployment requirement — which is what keeps the session cookie at `samesite="lax"` and `CORSMiddleware` out of the backend entirely. A Next.js app-router instance is a *server*. Serving it from FastAPI means either running a second Node process, which reintroduces exactly the cross-origin cookie and CORS problem ADR-168 exists to avoid, or exporting statically, which discards most of what Next.js is for. The auth decision made the framework decision stronger a day later, and neither record noticed at the time.

Two things that blocked starting have since cleared: the omni-channel interview closed 25/25 with its ADRs written, so the campaign and variant screens can be designed against channel-shaped variants rather than retrofitted; and [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] removed the largest unknown surface in the manager UI.

## Decision

**1. The manager client is a plain React SPA built with Vite, with React Router used as a library.**
Vite produces a static bundle FastAPI serves. Routing is something the application calls rather than a framework that calls the application.

This is the plainest thing that works, and plainness is the point rather than an economy: the project's stated posture is principles over a fixed tech stack, and an adopter who wants something else is then changing a dependency rather than a paradigm. The cost is booked honestly in `### Negative` — route modules, data loading and pending states are written by hand that a framework mode would have generated.

**2. Next.js is rejected for this client, and not on principle.**
It is rejected because the profile does not match: no anonymous traffic, no SEO, no content-heavy public pages, and a same-origin deployment that wants a static bundle rather than a second server process. **The later public site is explicitly not covered by this record** — that decision belongs to the Phase 4 effort that builds it, and a tool rejected for an admin panel is not thereby rejected for a marketing site.

**3. The client authenticates with the session cookie, per [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]], and this record does not revisit it.**
`BETA-SCOPE` §5's step 2 — *"decide whether the frontend reuses that session or gets its own token exchange"* — is answered and built: the session cookie, with CSRF carried in an `X-CSRF-Token` header, and machine credentials kept deliberately separate because they are for orchestrators and CRMs rather than for a person at a screen.

**4. The API client is generated from the backend's OpenAPI schema, never hand-written.**
The backend already emits it. Hand-writing request and response types per screen would create a second description of the same contract, drifting silently — and the first thing to drift would be the channel-shaped fields [[ADR-160 — Channel Model and Composition]] took care to get right.

**5. The client lives in this repository, in `frontend/` beside `backend/`.**
Two couplings make a second repository a release-coordination problem rather than a separation: FastAPI serves the build output, and the typed client is generated from the backend's own schema. In one repository a single CI run can assert that the generated client still matches the schema it came from; across two, that check becomes a version-skew problem somebody has to remember. The playbook also ships as one thing an adopter clones, which is what the package is for.

**6. MJML compilation stays in this codebase, per [[ADR-131 — Email Module Templates Use MJML as Source Format]].**
That record already places compilation in the frontend layer and keeps the Python backend from ever invoking MJML. This decision inherits it rather than reopening it — worth stating, because "the frontend" was a hypothetical when ADR-131 was written and is now a directory.

## Consequences

### Positive

- **The scaffold is unblocked**, and with it `BETA-SCOPE` §5's MVP cut: campaign and variant builder, audience, prepare-send, and a read-only delivery view.
- **Less framework than the reflex answer**, on a client whose whole job is forms over a REST API — and a shorter learning surface for whoever maintains it, including an adopter.
- **A static bundle is what the deployment already wants.** ADR-168 made FastAPI serve the client; Vite's output is exactly that, with no second process to run, supervise or reverse-proxy.
- **The contract cannot silently fork**, because the client's types are generated from the schema rather than transcribed from it.
- **One repository, one CI run, one clone.** The check that the client still matches the backend is a build step rather than a convention.
- **Nothing here forecloses the public site.** It is a separate decision for a separate effort, and this record says so rather than leaving a precedent to be read as one.

### Negative

- **Boilerplate a framework mode would have written is now written by hand** — route modules, data loading, pending and error states, across a dozen screens. This is the cost of the plain choice and it is paid per screen, not once.
- **A monorepo means the backend suite and a frontend suite share a CI run**, and a slow or flaky frontend build slows the loop that 535 backend tests currently keep fast.
- **Same-origin serving is inherited as a hard requirement**, not chosen here. ADR-168 books that cost; this record makes it concrete by choosing a bundle FastAPI must serve, and an adopter who wants the client on its own host is changing the cookie policy and adding CORS themselves.
- **"Principles over a fixed tech stack" is now one stack further from true.** The repository already prescribes Python, FastAPI, Postgres and MJML; adding React and Vite is defensible individually and cumulative in aggregate, and an adopter who wants a different client has more to replace than the README implies.
- **A second language, toolchain and dependency tree enter a repository that has had one**, with its own supply chain, its own lockfile and its own upgrade cadence — none of which the ADR record or the migration convention currently covers.

## Notes

- **This ADR records a decision rather than making one.** The reasoning is BETA-SCOPE §5's, taken 2026-08-22 and confirmed with the user the same day; what is added here is the ADR-168 argument, the repository layout, and the routing choice BETA-SCOPE left as "React + Vite, **or** React Router in SPA mode". React Router's framework mode was the live alternative and would also have produced a static bundle — it was set aside for conventions rather than capability.
- **Deliberately not decided:** which generator produces the typed client, the styling approach, and the test tooling. All three are scaffold-time choices that a record made before the scaffold would be guessing at, and none of them is hard to change later. **All three were decided on 2026-09-20, in [[ADR-173 — The Manager Client's Runtime Dependencies]]**, at the scaffold as this line anticipated. That record also books the part this sentence got wrong: the component choice is not cheap to change once sixteen screens are written against it.
- **The brand/theming split is already decided elsewhere** and this record does not touch it: email keeps a full plain-CSS `brand.css` owned by designers, while the management UI gets a small palette of colours, fonts, sizes and logos applied through CSS custom properties. That is a `docs/backlog.md` item scoped for the final MVP package, and it constrains the styling choice above.
- **Open before the first screen — updated at acceptance, 2026-09-20.** Three items in the layer this client leans on hardest were logged on 2026-09-19. **Two are closed.** `brand_id` defaulting to every brand, and machine reads falling through to a platform-level `view`, both went with [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]: the working brand is now resolved for every request, `brand_id` is a required argument on every brand-owned service function, and a declared brand the caller holds no grant on is refused explicitly.

  **One remains, and it is the one this record said matters most.** Every page view still runs four or five `SELECT`+`UPDATE`+`COMMIT` cycles against the same `auth_sessions` row, because `user_for_token` writes `last_seen_at` and commits on every call and five call sites reach it. A Jinja page is one request; a React screen is five to fifteen, and this is write amplification rather than read — a user with several tabs open already serialises on that row's lock. The property being paid for is real and must survive any fix: the session's `brand_id` is a cache revalidated against the grant table on every resolution, which is what makes a revoked grant stop working immediately. Logged in `docs/backlog.md`; **not a blocker for scaffolding the client, and a blocker for judging it under load.**

## Related ADRs

### Depends On
- [[ADR-002 — API First Architecture]]
- [[ADR-131 — Email Module Templates Use MJML as Source Format]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]
