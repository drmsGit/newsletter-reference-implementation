---
type: adr
status: accepted
topic:
  - architecture
  - frontend
created: 2026-09-20
source:
  - "The three items ADR-170's Notes left open, decided at scaffold time; component comparison measured 2026-09-20"
depends_on:
  - "[[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]"
  - "[[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]"
  - "[[ADR-171 — Nothing Required to Run This Platform Is Commercial]]"
---

## Status
Accepted

## Context

[[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] chose the framework and deliberately stopped there. Its Notes say so: *"Deliberately not decided: which generator produces the typed client, the styling approach, and the test tooling. All three are scaffold-time choices that a record made before the scaffold would be guessing at, and none of them is hard to change later."* That was the right refusal at the time. It stops being right now — the Phase 0 backend work landed 2026-09-20, the scaffold is the next thing to happen, and a choice made at the scaffold is no longer a guess about a directory that does not exist.

**[[ADR-171 — Nothing Required to Run This Platform Is Commercial]] point 1 is the constraint that actually decides this record**, and it decides it against the option that was otherwise winning. Every component required to run the platform must be open-source and self-hostable; required means that with it absent or unpaid, the platform does not work. A component library whose only in-family answer to "show a table" is a paid tier is not an adapter behind a seam — it is the management UI's list screens.

The comparison below is of **current published state, measured 2026-09-20**, not of reputation. That distinction did most of the work: two of the three candidates have a reputation that their repositories no longer support.

**Radix UI is rejected on maintenance and on a hole.** Releases stopped between Aug 2025 and Jun 2026 — roughly ten months — the last commit is 31 Jul 2026, every recent commit is by a single WorkOS employee, and 151 PRs are open. The hole is independent of the maintenance: **there is no combobox**, and issues #1342, #1486 and #2337 make that a settled non-answer rather than a pending one. An entity picker that a person can type into is not a nice-to-have in a screen set whose job is choosing content, audiences and providers, so Radix means a second primitives dependency for the one control most screens need.

**Base UI is rejected, and it was the recommendation.** `@base-ui/react` 1.8.0 is the healthiest of the three by a clear margin — GA Dec 2025, monthly minors, around seven maintainers including the people who created Radix — and on maintenance health alone it would be the answer. It loses on one thing: **it has no table primitive, and the in-family answer is MUI X Data Grid, whose useful tier is paid.** That fails ADR-171 point 1 directly. Rejecting the healthiest option on a licence rule is the rule doing what it exists to do; ADR-171's own Positive claims *"a rule exists that a future dependency can fail"*, and this is the first dependency to fail it.

React Aria is the only candidate that ships an accessible Table, GridList and Tree under a permissive licence, which is what makes it the answer rather than the preference.

**The licence point is stated rather than left to inference, because inference would get it wrong.** React Aria is **Apache-2.0** — the first non-MIT entry in the required stack. ADR-171 point 1 says "open-source and self-hostable", not "MIT", so Apache-2.0 satisfies the rule as written. But point 1's own text enumerates a stack that happens to be all MIT, and a reader who takes the enumeration for the rule would read a constraint into it that is not there. Saying which of those two the rule is costs one sentence here and is unrecoverable later.

## Decision

**1. Components are `react-aria-components` (Adobe), styled with plain CSS over CSS custom properties.**
React Aria supplies behaviour and accessibility and holds no visual opinion, which is the property that matters: it leaves intact the brand/theming split [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]'s Notes already record, where email keeps a full plain-CSS `brand.css` owned by designers and the management UI gets a small palette of colours, fonts, sizes and logos applied through CSS custom properties. A library with its own design system would have had to be overridden into that split rather than dropped into it.

Radix and Base UI were the alternatives and the reasons they lost are in Context, measured rather than recalled. The licence fact is part of the decision, not a footnote to it: **Apache-2.0 enters an otherwise-MIT required stack here**, permitted by ADR-171 point 1 as written.

**2. The API layer is `openapi-typescript` (types only) plus `openapi-fetch`, with TanStack Query over them.**
This is how [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 — *"generated, never hand-written"* — is actually satisfied. Types-only generation produces **one `.d.ts` an adopter can read**, rather than several hundred generated functions an adopter scrolls past; for a package whose purpose is to be read and copied, the generated artefact being legible is a requirement rather than a nicety. `openapi-fetch` is about 6kb and is type-safe against exactly those types, so the fetch layer is a thin thing that cannot drift from the schema independently. It is also the one place [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] point 2's `X-CSRF-Token` header is attached — a client with one fetch layer has one place to get that right, which a per-screen `fetch` call would not.

**TanStack Query earns its place on one concrete requirement, not on ergonomics.** [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]] resolves the working brand into every query, which means **a brand switch must invalidate every cached query in the client.** Hand-rolled, that is a per-screen correctness problem across sixteen screens with nothing to catch a miss — and the failure mode is the worst available one, a screen showing another brand's rows after a switch that appeared to succeed. A cache with a first-class invalidation story turns sixteen chances to be wrong into one.

**3. Testing is Vitest plus React Testing Library, with a contract script beside them.**
`npm run check:contract` regenerates the client from `GET /openapi.json` and fails on a diff. That script is the specific check [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 5 promises when it says the client-matches-backend check *"is a build step rather than a convention"*.

**4. This record creates no CI, and says so rather than implying otherwise.**
ADR-170 point 5's Positive — *"one repository, one CI run… the check that the client still matches the backend is a build step rather than a convention"* — currently has no infrastructure under it. **There is no `.github/` directory and no CI of any kind in this repository, verified 2026-09-20.** Point 3 gives that sentence a script; it does not give it a run. Booking the shortfall in the Decision keeps it from being read as closed by the record that adds the script.

## Consequences

### Positive

- **The scaffold is unblocked.** The three items ADR-170 deferred are the three items a scaffold has to answer on its first day, and none of them is now a guess.
- **One accessibility model across the app**, with real grid semantics available the first time a list screen stops being a list and starts being interactive — which is the case Radix and Base UI could not serve without a second dependency or a paid tier.
- **The contract check exists as something runnable.** A convention that a person remembers and a script that a person runs are different objects, and this record produces the second.
- **All three dependencies are permissively licensed and self-hostable**, so [[ADR-171 — Nothing Required to Run This Platform Is Commercial]] point 1 holds across the client with nothing argued as an adapter.

### Negative

- **Apache-2.0 enters an otherwise-MIT required stack.** This is not a rule violation and it is not free either: Apache-2.0 is a licence some organisations route through a legal-review step and MIT is one they wave through, and **a reference architecture is copied by people whose constraints are not ours**. The cost lands on the adopter rather than on this repository, which is the kind that is easiest to not notice.
- **React Aria's Toast has been `UNSTABLE_` for roughly eighteen months** — alpha since March 2025, still alpha. Notifications are therefore either hand-rolled or built on an unstable API, and **that call is owed before any screen shows one**. Choosing the library does not choose this, and the gap is real rather than theoretical: every write screen wants a toast.
- **React Aria is more verbose and more opinionated about DOM structure than either alternative.** That cost is paid in a codebase whose stated purpose is to be read and copied, so verbosity is not merely a typing cost — it is the thing an adopter reads first.
- **ADR-170's Negative about accumulating stack gets worse by three runtime dependencies**, and this is the second record in three days to add to it. *"Principles over a fixed tech stack"* was one stack further from true on 2026-09-19; it is three dependencies further from true now, and the cumulative number is the one that matters rather than each defensible increment.
- **Point 4 means the contract check is a convention until somebody runs it** — which is precisely the shape ADR-170 point 5 says it should not be. The script exists, the run does not, and the gap is booked here rather than discovered when the client and the schema have already forked.
- **TanStack Query introduces a second state model beside React's own**, to be learned before the first screen rather than after it. The requirement in point 2 is real, and so is the fact that a maintainer now has to know which of two places a piece of state lives in.

## Notes

- **The comparison was measured on 2026-09-20 and is of current published state, not of reputation.** Radix in particular reads as the safe, obvious choice from memory and does not survive a look at its commit log; Base UI reads as the newcomer and is the healthiest of the three. Anyone revisiting this should remeasure rather than re-remember — all three facts have a date on them and none of them is stable.
- **Base UI was the recommendation on maintenance health and lost specifically on the table primitive.** Recording that is the point: if MUI ever ships an accessible table under a permissive licence, or Base UI grows its own, the argument that decided this record disappears and the decision is worth reopening. Nothing else about the comparison changed the answer.
- **The Toast decision is owed.** `UNSTABLE_` for eighteen months is long enough that "wait for it" is not a plan. Hand-rolled or unstable-API, decided before the first screen that notifies — logged as an open item rather than left to be settled by whoever writes that screen first.
- **This record does not touch MJML.** [[ADR-131 — Email Module Templates Use MJML as Source Format]] places compilation in the frontend layer and [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 6 inherits that rather than reopening it. It is still not wired anywhere, and choosing component, API and test dependencies does not advance it — the frontend layer that ADR-131 assigned the work to now exists as a directory and still does not compile a template.

## Related ADRs

### Depends On
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-171 — Nothing Required to Run This Platform Is Commercial]]
