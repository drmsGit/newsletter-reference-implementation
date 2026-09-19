---
type: adr
status: accepted
topic:
  - architecture
  - security
  - access
  - frontend
created: 2026-09-19
modified: 2026-09-19
source:
  - "User decision, 2026-09-19 (raised while scoping the React manager frontend)"
depends_on:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-151 — Authentication and Sessions]]"
  - "[[ADR-152 — Secret and Credential Handling]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
enables:
---

## Status
Accepted

## Context

The React manager frontend is blocked on one question: how a person sitting in front of it proves who they are to the JSON API. [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] closed launch gate 3 by putting a guard over the twelve JSON routers, and the build notes that accompanied it narrowed the plane to machine credentials only — *"The JSON API takes a machine credential and not a session cookie."* That narrowing is what this record revisits. It sits in that record's Notes rather than its Decision, which is why what follows is an addendum to ADR-166 and not a supersession of it; see the Notes below.

**The reason that carries the most weight is the audit actor.** The middleware in `backend/main.py` populates `request.state.current_user` from the session cookie on *every* request, the JSON plane included, because it is registered as an application-wide `@app.middleware("http")` and not as a router dependency. `record_from_request` (`backend/app/audit/service.py:94-104`) reads exactly that, plus `request.state.current_brand`. So on a cookie-authenticated JSON request the right actor, the right actor type and the right brand are already on the request object, and the audit log is correct with **no new code and no new mechanism**. Every other option has to build something to get the same answer, and one of them cannot get it at all.

Three further reasons follow it. There is **no schema change and no migration**: there is no Alembic in this repository — tables come from `create_all` plus hand-written `backend/scripts/migrate_*.sql` — so avoiding a migration is worth more here than the phrase usually implies. There is **one working-brand mechanism per human across both clients**, the session's brand via `request.state.current_brand`, already set on JSON-plane requests. And the move is one [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 8 already blessed a level up: *"One rule — a brand-scoped permission is checked against the brand this request is working in — gains a second way to say which brand, and not a second rule."* This applies that shape to identity. One policy, a second way to say who.

**There is precedent for two mechanisms on this plane, and it is deliberate.** `backend/app/auth/policy.py:42-45` records it in the file somebody auditing the policy would actually read: platform-issued credentials authenticate systems the adopter controls, provider signature verification authenticates send providers who cannot hold a credential this platform issued, and *"neither is a degraded version of the other"*. This decision makes it three. It does not invent the shape.

[[ADR-142 — Autonomous Workflows and the Automation Boundary]] §2 also has a stake in the answer. It requires that **every action an orchestrator can trigger must also be triggerable in-app**, which is a claim about parity between the two planes. While the manager client is Jinja templates over `/ui/*` and the orchestrator calls JSON, that parity has to be maintained by hand across two route sets. A manager client that speaks the same JSON API makes it structural instead — the same routes, the same policy table, two kinds of principal — which is why this decision strengthens §2 rather than merely being compatible with it.

Three options were weighed and rejected, and the reasons are worth keeping because two of them are real.

**A short-lived bearer token minted for a human session** is genuinely viable and was rejected on two costs. It leaves `request.state.current_user` as `None`, so every audit row from the SPA records a NULL actor — silently. The honest-null reasoning in `record_from_request` was written for the case where access control is switched off and nobody is signed in; under a token-bearing SPA it would become a systematic lie told by a docstring that reads as careful. Its second cost is storage, and each honest shape costs something: reusing `auth_sessions` produces a token that is not actually short-lived, while a third table creates a second revocation surface that `set_active` must learn about or human offboarding regresses into precisely the hole [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]'s `### Negative` books for machine credentials. Someone who treats *no ambient credential on the API* as a load-bearing property rather than a convenience would reasonably choose this option instead, and that should be recorded rather than argued away.

**An integration credential held by the SPA** ships a machine secret in JavaScript. It also collapses every operator into the single `IntegrationDB` audit actor that [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 3 spent a whole point establishing as durable across rotation, and it grants every logged-in person the union of that credential's grants regardless of their own role — which defeats [[ADR-150 — Tenancy and Access Model]] point 5 by the same route a payload defeats a URL. `docs/business/BETA-SCOPE.md:248-254` reached the same conclusion independently while sketching the frontend: keep the frontend's session transport separate from gate 3's machine keys, because *"conflating the two auth mechanisms would be a mistake."*

**Content-negotiating the existing `/ui/*` routes** is a real option rather than a straw one: the seam already exists. `_wants_html(request)` is defined in `backend/main.py` and all four exception handlers already branch on it. It is rejected on volume and on principle. On volume, `backend/app/frontend/router.py` holds 57 POST routes written in a `Form(...)`-in, `RedirectResponse`/`TemplateResponse`-out idiom with 303-after-POST throughout, and retrofitting a JSON contract onto them is a rewrite wearing a negotiation header. On principle, it would make the UI own the API contract — the inverse of [[ADR-002 — API First Architecture]], and a shape in which every future API change is a template change.

## Decision

**1. `enforce_api_policy` accepts two credential types, and the principal is already typed for it.**
The guard tries the machine credential first — `Authorization: Bearer <key_id>.<secret>` — and, failing that, resolves the `nra_session` cookie through `user_for_token`. The resulting principal is `UserDB | IntegrationDB`, which is the `Principal` type already declared at `backend/app/auth/service.py:816`.

`policy.py` and `permissions_for` are **untouched**. `permissions_for` (`backend/app/auth/service.py:819-834`) already dispatches on the principal's type — a person's permissions arrive through a role, an integration's directly — and the same policy table already decides which permission a route needs. Adding a second way to say *who* therefore changes the credential reader and nothing below it. That is [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 1's promise kept literally rather than approximately: one access model answers "may this caller do this here", and this decision does not add a second.

**2. CSRF returns to this plane, defended with a header-borne token.**
A new `enforce_api_csrf` compares an `X-CSRF-Token` request header against `csrf_token_for(session_token)` (`backend/app/auth/service.py:65-82`) using `secrets.compare_digest`. No storage, no column, no new secret to rotate: the primitive exists, is derived from the session token rather than kept server-side, and is already domain-separated from `hash_secret` so it cannot collide with the session hash in `auth_sessions.token_hash`.

**The existing `enforce_csrf` cannot be reused, for two independent reasons.** It calls `await request.form()` (`backend/app/auth/dependencies.py:173`), which against a JSON body returns an empty `FormData` rather than raising — so it would find no token and refuse every JSON write. And it returns early when there is no session cookie (`backend/app/auth/dependencies.py:169-171`), so on a bearer-only request it is silently inert. A guard that refuses everything on one plane and does nothing on the other is not a guard that was reused; it is two bugs sharing a name.

**3. Same-origin serving is a stated deployment requirement, not an adopter's choice.**
FastAPI serves the built SPA; Vite proxies to the backend in development. This is what keeps the session cookie at `samesite="lax"` (`backend/app/auth/router.py:165`) and keeps `CORSMiddleware` out of `backend/` entirely — there is none today, verified. A cross-origin frontend would require both a `samesite="none"` cookie and a CORS policy, which is two new controls to get right in exchange for a deployment shape nobody asked for.

**4. A request carrying both a bearer credential and a session cookie is refused outright.**
Not silently preferred one way or the other. The cost of preferring is not ambiguity in the guard — a guard can always pick — it is that the audit row then names a principal nobody can predict from reading the request. Refusing is the only answer that keeps "who acted" derivable from what was sent.

## Consequences

### Positive

- **The SPA becomes buildable.** The one blocking question in `docs/business/BETA-SCOPE.md`'s frontend sketch — reuse the session or mint a token — is answered, and answered in the direction that needs no new storage.
- **The audit actor is correct for free.** `record_from_request` yields the right actor, actor type and brand on SPA requests with no new code, because the middleware already resolved them. No write path is revisited, which is the property [[ADR-153 — Audit and Accountability]] point 3 was designed to buy.
- **Zero schema change, zero migration, no new table.** In a repository whose migrations are hand-written SQL beside `create_all`, that is a real saving rather than a stylistic preference.
- **One working-brand mechanism per human, across both clients.** A person's brand comes from the session in the Jinja UI and from the session in the SPA. The brand switcher does not grow a second implementation, and [[ADR-150 — Tenancy and Access Model]]'s 2026-09-15 addendum keeps meaning one thing.
- **`policy.py` and `permissions_for` are untouched**, so [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 1 holds in fact and not only in intent: there is still exactly one place that answers "may this caller do this here", and it did not need to learn that a browser exists.

### Negative

- **An ambient credential returns to a plane whose guard docstring was written to celebrate not having one.** `enforce_api_policy`'s docstring states that the narrowing "buys the CSRF question outright". That sentence stops being true the moment this lands. CSRF becomes a control this codebase must get right and then keep right, which is a permanent obligation rather than a one-off edit, and the docstring must be rewritten rather than left to read as reassurance.
- **A new guard must be wired at the `_api` list in `backend/main.py`, and that wiring line is exactly the shape of the 2026-09-18 bug.** `enforce_csrf` was wired onto the frontend router alone, which left the thirteen user- and role-administration forms in `auth_router` — the most privileged forms in the system — with no CSRF protection, while `docs/business/LAUNCH-GATES.md` recorded gate 4 as "CSRF on all 62 forms". A guard added to eleven of twelve routers fails identically and reports identically: a gate that reads as closed over a plane that is open. The list is one line and it is the line that matters.
- **Same-origin becomes a deployment requirement adopters inherit.** That cuts against the adapt-it-to-your-setup stance visible everywhere else in the deployment surface — `system_mail_provider`, `trust_proxy_headers` (`backend/app/auth/service.py:577-591`) and the provider adapters all let an adopter choose. Here they do not, and an adopter who wants the frontend on its own host is changing the cookie policy and adding CORS themselves, with their own reasoning.
- **A docstring this decision makes false ships until it is fixed.** `backend/app/recipients/router.py:55-57` states that *"A cookie-authenticated caller cannot reach this route at all (the machine plane takes no cookies), so `principal` is an integration or the guard has already refused."* The guard around it is payload-dependent and correct either way, but the comment explaining why is not, and a false comment about who can reach a consent-writing route is the expensive kind.

## Notes

- **Built 2026-09-19.** All four points, plus the prerequisite this record's own
  Notes identify as non-optional. Three things are worth recording because they
  were decided during the build rather than in the record:

  **The brand asymmetry is ADR-166 point 8's, reused rather than invented.** A
  person's working brand comes from the session — already on `request.state`,
  put there by middleware that runs for these routes too — and a machine states
  one per request. The SPA therefore sends no `X-Brand` and is never asked for
  one, which is what stops part 1 refusing every brand-scoped write with a 400.

  **The guard writes the resolved brand back onto `request.state.current_brand`,**
  as this record's Notes prescribe, so `content`, `campaigns` and `audience`
  stop writing rows to the default brand while checking the permission against
  a declared one. Their PROVISIONAL comments are replaced rather than amended.

  **The approval gate became machine-only.** `may_send_unattended` is a column
  on an integration and does not exist on a user, so the check is now reached
  only by a bearer-authenticated caller — a person firing a send *is* the
  approval, which was implicit while people could not reach this plane at all.

- **Addendum 2026-09-19 — approving over the API, decided and not yet built.** This record put people on
  the JSON plane, which silently changed what "no approve over the API" means. It was written as an
  absolute — the guard's own text says "there is deliberately no way to approve over the API" and a test
  asserts no such route exists — and the reasoning was about machines: *a machine that can approve its
  own held request has defeated the mechanism.* With a person on this plane, the absolute now says
  something different and unintended: **the React client cannot show or work an approval inbox at all**,
  which matters more since [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] made
  that inbox close to the manager's home screen.

  **Decided: approving requires a session-authenticated person, and is refused to a bearer credential.**
  The original property is kept exactly — a machine still cannot approve anything, including its own
  request — while the SPA gets the surface it needs. The assertion changes from "no such route exists"
  to "a bearer credential is refused here", which is the sharper claim anyway, because it tests the
  property rather than its absence.

  Not built; logged in `docs/backlog.md`. What a machine may still do is unchanged: **request** approval,
  which is the whole of ADR-166 point 5.

- **The `enforce_csrf`-on-one-router shape this record warns about is now
  asserted, not just avoided.** A test walks every JSON write route the app
  registers and fails if one lacks `enforce_api_csrf`. Its first version read
  `route.dependencies` and found nothing at all — FastAPI merges router-level
  dependencies into `route.dependant`, so the test could never have caught the
  bug it is named after. Reading the resolved dependant is what makes it real.

- **This is a dated addendum to [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], not a supersession, and the distinction is load-bearing.** What it reverses — *"The JSON API takes a machine credential and not a session cookie"* — sits in that record's build-notes section, not in its Decision. ADR-166's Decision says nothing about cookies; point 1 says a machine caller is a principal in the same access model, and explicitly does not say whether a person may use the JSON API. The narrowing was an implementation answer taken on 2026-09-18, and it is the implementation answer that changes here. **This repository has had exactly one supersession ever — [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001, on 2026-09-12 — and this is deliberately not a second.** The addendum text ADR-166 needs is reported with this record rather than applied to it.
- **Sequencing: the open P1 in `docs/backlog.md` is a prerequisite, not a preference — part 1 does not function without it.** `enforce_api_policy` calls `_declared_brand(request)` unconditionally for a brand-scoped permission and raises `BrandNotDeclared()` when the header is absent (`backend/app/auth/dependencies.py:377-386`). A cookie-authenticated person sends no `X-Brand` — their brand is in the session — so landing part 1 alone refuses **every brand-scoped SPA write with a 400**, which is the whole campaign, content and audience surface. Verified 2026-09-19. The same P1 also has the routers checking the permission against the declared brand and then writing the row to the default brand — `brand_id=ensure_default_brand(db).id` at `backend/app/content/router.py:151`, `backend/app/campaigns/router.py:57` and `backend/app/audience/router.py:27`, each under a PROVISIONAL comment whose first clause is now false. The fix that serves both planes is to have the guard write the **resolved** brand onto `request.state.current_brand`: for a machine, the declared header after the grant check has passed; for a human, already set by the middleware. One path then serves both. Fixing it instead with an unvalidated `payload.brand_id` would let a payload choose the scope its own authorization was evaluated in, which is the defect [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 8 explicitly rejects when it refuses to derive the brand from the addressed resource.
- **Unblocked by this but deliberately not decided here:** `enforce_api_policy` setting `request.state.principal` and a derived actor type, with `record_from_request` preferring it over `current_user`. That is also what [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 3's `ACTOR_INTEGRATION` needs: the constant is defined at `backend/app/audit/service.py:43` and **nothing writes it**, so no audit row in this system has ever named an integration as its actor. Note the shape changed on 2026-09-19, the same day: `backend/app/approvals/service.py` writes audit entries **from a service with an explicit actor**, departing deliberately from `audit/service.py`'s written-from-routes rule on the grounds that an expiry has no request behind it at all — which is the revisit that module's own docstring named as "the first thing to revisit" — and it adds a third actor type, `ACTOR_SYSTEM`. So the machine plane is no longer silent; it is specifically the *integration as actor* that remains unwritten.
- **The framework choice is a separate record and is owed.** React over the alternatives is not decided by this ADR and must not be read into it; this record decides only how the manager client authenticates and where it is served from.

## Related ADRs

### Depends On
- [[ADR-002 — API First Architecture]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-151 — Authentication and Sessions]]
- [[ADR-152 — Secret and Credential Handling]]
- [[ADR-153 — Audit and Accountability]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
