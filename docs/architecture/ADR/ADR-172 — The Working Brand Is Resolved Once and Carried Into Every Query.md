---
type: adr
status: proposed
topic:
  - architecture
  - security
  - access
  - api
created: 2026-09-19
source:
  - "Router sweep for the React migration (docs/react-migration-inventory.md, 2026-09-19) and CODE_REVIEW_2026-09-19 P1-02"
depends_on:
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
  - "[[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]"
  - "[[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]"
---

## Status
Proposed

## Context

[[ADR-150 — Tenancy and Access Model]] point 2 says the brand a request is working in "is carried into the queries that read them". On the Jinja plane it is. On the JSON plane it never has been, and the sweep that established this is not a reading of the design but a count of call sites.

**The Jinja router passes `brand_id` at 15 call sites. The JSON routers pass it at none.** `content/router.py:59` calls `list_content_records(db)`; `campaigns/router.py:58` calls `list_campaigns(db)`; `audience/router.py:27` calls `service.list_groups(db)`. Each of those service functions takes `brand_id` with a default of `None`, and `None` means every brand. `content/router.py:96` is worse than a forgotten argument: it calls `get_content_record(db, content_id)`, and `get_content_record` (`content/service.py:44`) **takes no `brand_id` parameter at all**, so there is nothing to forget and nothing to pass. The consequence, stated as the plain fact it is: **`GET /content/`, `GET /content/{id}`, `GET /campaigns/` and `GET /api/audience-groups/` return every brand's rows to any authenticated caller.**

The root cause is one line in the guard. `auth/dependencies.py:427` reads `brand_id = None`, and the resolution that follows sits inside `if is_brand_scoped(permission):` — the same block that then writes `request.state.current_brand = {"id": brand_id}`. Every GET maps to `view`, the 2026-09-15 addendum classifies `view` as platform-level, so a read takes the `elif` branch: it never resolves a brand and never writes one. **Context — "which brand is this request working in" — and authorisation — "is this permission checked against a brand" — are the same line of code, and they are not the same question.**

`view` did not land platform-level by oversight. It is a single permission key guarding rows of both kinds — campaigns and settings, content and users — so the addendum's own classification rule, *"a permission is brand-scoped if the rows it guards carry a `brand_id`"*, cannot classify it. The rule is sound and `view` is outside its domain. That is the defect: a rule that decides authorisation was also, silently, deciding context.

This is the read side of the external review's 2026-09-19 **P1-02** finding — writes authorised against the declared brand while rows are addressed by bare id. `docs/backlog.md` carries both halves as separate entries and `docs/react-migration-inventory.md` draws the conclusion: **B1 and P1-02 are one finding, not two.** The brand boundary does not exist on the JSON plane in either direction, and the two directions are the same missing argument seen from opposite ends.

The timing is [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]'s. The SPA calls these endpoints directly rather than through a Jinja route that has already resolved the working brand, so the caller-side mitigation this default has been relying on goes away at exactly the moment the JSON plane becomes the only plane. **Deleting the Jinja UI therefore does not move this boundary. It removes it.**

## Decision

**1. Every request resolves a working brand, whether or not the permission is brand-scoped.**
The resolution moves out from under the `is_brand_scoped` branch. A person's working brand comes from the session — the middleware already resolves it onto `request.state` — and a machine declares one in the `X-Brand` header. The guard writes the resolved value to `request.state.current_brand` in both cases. This splits **context** from **authorisation**: the brand a request is working in is established for every request, and whether a permission is checked against that brand remains the addendum's question, answered as it is today. The asymmetry between the two principal types is [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 8's — *"a human's working brand comes from the brand switcher and rides in the session; a machine has no session to carry one, so it states one per request"* — reused here rather than invented, and unchanged by being applied to reads.

**2. The resolved brand must be one the principal holds a grant on, and that is checked explicitly.**
For a brand-scoped permission the check is already implied: `has_permission(db, principal, permission, brand_id=brand_id)` fails if there is no grant on the declared brand. For a platform-level permission it is not implied, because the permission is checked without a brand at all. Without an explicit check, a machine holding only `view` could declare any brand in `X-Brand` and read it — which would replace one leak with a more convincing one.

The cost is worth stating plainly rather than discovering later. **On reads the *filter* enforces the boundary, not the permission check.** That is precisely why this check must be real rather than implied: it is the only thing standing between a declared brand and the rows selected against it, and on the read path nothing else will catch a brand the principal does not hold.

**3. No fallback, on either plane.**
A brand-owned operation that cannot resolve a working brand is refused. ADR-166 point 8 already rules this for writes — the mitigation for an ambiguous refusal is an error that says which of the two happened, *"not a fallback to 'the single brand this integration holds', which would work right up until it holds two, and would fail by silently acting on the wrong brand rather than by refusing"* — and this record extends the same refusal to reads. Reading the wrong brand's rows is quieter than writing them and no more correct.

`ensure_default_brand` is not a fallback on the JSON plane. **`working_brand_id` (`frontend/router.py:65`) does fall back to the default brand**, and that is defensible exactly where it lives and nowhere else: it covers access control switched off, so nobody is signed in, and a user holding no grant at all, who cannot reach a write route anyway because `enforce_policy` refuses them first. Both conditions are properties of the Jinja plane. **It must not be lifted onto the JSON plane**, where a machine principal always exists, always holds grants, and a default brand would be a silently wrong answer instead of a usable one.

**4. `brand_id` becomes a required argument on every brand-owned service function.**
No defaults. Genuine spanning callers — platform counts, migrations, seeds, tests — get explicit `list_all_*()` functions that say in their name what they are doing. Forgetting the brand becomes a `TypeError` at the call site rather than a leak in production.

This follows [[ADR-163 — Per-Channel Consent and Addressability]]'s addendum, which already ruled it for the consent path: *"Every read path gains a dimension it must be passed rather than default, since a defaulted brand inside a gate is exactly the fail-open this addendum refuses."* The same repository already made this call once — `is_consenting_filter` takes brand as a required positional on the stated reasoning that forgetting it is a `TypeError` — and the list functions took the opposite direction twelve files away. This settles the two on the same answer. **Measured 2026-09-19, not estimated:** of the sixty-eight public service functions in campaigns, content, audience and delivery, **eight already take a brand and sixty do not** — and tellingly the eight are the creates and the lists, the places somebody already noticed. Subtracting the category vocabulary, which stays global, and the cross-brand sweeps, which become `list_all_*()`, leaves **45–50 functions that change**, reached from **291 call sites**.

**5. Nested resources prove ownership by joining to the owning root in the same query that selects the target.**
**No `brand_id` column is added to any nested table.** ADR-150's transitive-ownership principle holds and is the reason: *"Which content is Beach is therefore already per-brand, transitively, with no column of its own."* The five owning roots are `campaigns`, `send_instances`, `content_records`, `audience_groups` and `consent_events`. The deepest chain is three hops — `DecisionResolutionDB → DecisionSlotDB → VariantDB → CampaignDB.brand_id`.

The join goes in the **same** query as the selection, atomically. An out-of-brand row is **not found**, rather than found and then rejected, so there is no window between checking and acting and no code path where a row has been loaded and something still has to remember to refuse it.

**6. An out-of-brand row answers exactly as an absent one — 404 — and the server logs the real reason.**
`frontend/router.py:850` already does this deliberately, and says why: *"A hard filter that filters only lists is not a hard filter — another brand's campaign would still open by URL, and a guessable integer id is not a secret."* No ADR has previously covered it — [[ADR-151 — Authentication and Sessions]]'s identical-response rule is scoped to the login form and its account-enumeration oracle — so the rule is recorded here for the JSON plane rather than left as a convention in one route's comment.

The risk this bounds is bounded already by ADR-150 point 1's single-tenant-per-deployment stance: brands are one company's brands, so cross-brand enumeration means an internal operator learning a sibling brand's id, not a customer learning another customer's. The accepted cost, stated rather than discovered: **a developer whose `X-Brand` is wrong sees "not found" and goes hunting a phantom missing record.** The diagnosis lives in the server log, on our side of the wire, which is the trade being made on purpose.

**7. Enforcement lives in the service query, not in the router.**
The router passes the brand; the query binds it. ADR-150 point 2 says the brand is "carried into the queries that read them" and left the layer open; this closes it. Putting the filter in the router would make every new route a place the boundary can be forgotten, and a forgotten filter in a router is invisible. In the service it is a signature. **A router that forgets cannot compile**, by point 4.

## Consequences

### Positive

- **The boundary stops depending on the presentation layer.** Retiring the Jinja UI moves the enforcement rather than deleting it, which is the property [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] needs and does not have today.
- **Forgetting becomes a `TypeError`.** Every entry in the brand change-impact table turns from a silent leak into an error at the call site.
- **One rule serves both planes.** A person's brand comes from the session and a machine's from a header, but after resolution there is one working brand, one filter and one refusal — not a UI rule and an API rule that can drift apart.
- **ADR-150 point 2 becomes true of the JSON plane for the first time.** Read and write sides of P1-02 close together, as the one finding they are.

### Negative

- **Forty-five to fifty service signatures change, and every caller changes with them** — seeds, scripts, tests and the Jinja router included. There is no incremental version of point 4: a required argument is required everywhere the day it lands.
- **Half the churn is in the test suite, which is the safety net being moved.** Of the 291 call sites, 145 are in `app/` and **146 are in tests and scripts** — four create functions alone account for 84 of them. Editing the tests that would catch a mistake, in the same pass as the mistake could be made, is the real risk in this work. It argues for a keyword-only argument with no default, so a missed call site raises at the moment the test runs rather than letting an existing positional slide into the new slot.
- **A machine must now declare `X-Brand` on reads too.** That is a contract change for any existing integration, and an integration that worked yesterday stops today with a refusal it has never seen before.
- **Nested queries gain up to three joins on the hot path.** The deepest chain in point 5 is paid on every resolution read, not only on the rare ones.
- **Point 2's explicit grant check is a new thing every future read route must not forget** — which is the same silent-default shape being removed here, wearing a different hat. It is centralised in the guard for exactly that reason, and that is a mitigation rather than a cure.
- **404 hides a wrong-brand declaration from the caller.** Point 6 takes this deliberately; it is still a cost, and it is paid by developers far more often than by attackers.

## Notes

**Explicitly not decided here.**

- **The build order.** An accepted ADR is not an implementation plan, and a final-design pass follows this record: where each part lands, which existing functions it reuses, what it deliberately does not touch, and what could break.
- **The category vocabulary stays global and unbranded.** Already settled by ADR-150's 2026-09-15 addendum, and point 5's refusal of new `brand_id` columns is the same principle, not a reopening of it.
- **The `X-Brand` header spelling.** That is ADR-166's to decide and it has decided it; this record only extends when it must be sent.

**Code facts verified 2026-09-19** against `auth/dependencies.py`, `content/router.py`, `content/service.py`, `campaigns/router.py`, `audience/router.py` and `frontend/router.py`. Line numbers in this record are as of that date and will move.

## Related ADRs

### Depends On
- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
