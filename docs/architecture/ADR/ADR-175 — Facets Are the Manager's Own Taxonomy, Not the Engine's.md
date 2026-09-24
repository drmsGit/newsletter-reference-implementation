---
type: adr
status: accepted
topic:
  - architecture
  - content
  - governance
  - data-model
  - frontend
created: 2026-09-24
source:
  - "[[Manager Workflow - design interview]] Cluster 2, questions 8–14, resolved 2026-09-21"
depends_on:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]"
---

## Status
Accepted

## Context

This system has a taxonomy already, and it is not the manager's. [[ADR-080 — Human-governed Taxonomy Before AI Selection]] makes categories the governed vocabulary for content **selection** — humans define categories, relations and relevance boundaries so that AI ranks inside a set a person drew. It says nothing about *finding* anything, and it was never meant to. The user said so directly on 2026-09-21, and the sentence is what opened this whole question: *"CategoryDB and the whole 'categorize content' is ONLY meant for the 'build a dynamic affinities profile of each recipient'."*

**What is missing is the other half of the same word.** A manager with a few hundred records needs to narrow by the axes their own business runs on: *"this could be a filter to distinguish b2c / b2b content, or to match content to IATA destinations or countries or regions, or to separate product from company information … Only they can decide how they typically group content."* That is filing, not affinity. Nothing in this repository serves it, and the surfaces that need it most are the two that are being designed right now — the content list, and the campaign builder's content picker, which is *"a dropdown with all content record ids"* today.

**The boundary is the load-bearing part of the answer, not a caveat attached to it.** If such a label can reach the decision engine, it *is* a category and ADR-080 governs it. If it must never, the separation has to be structural rather than conventional. Today nothing stops anybody reusing `CategoryDB`: it feeds decision-slot candidate filtering through the allowed- and excluded-category limits that [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]] requires every slot to declare, and it feeds the signal layer through `signal_contributions`, which carries a category per contribution. A manager filing a record under "B2B" in that table would silently make "B2B" an affinity dimension of every recipient who engages with it — no error, no warning, a corrupted profile. `CategoryDB.type` is `main`/`sub` (`backend/app/content/db_models.py:26`), which is a hierarchy level rather than a purpose, so it is **not the seam it looks like**; adding a third value to it would be a convention, and conventions are exactly what the failure mode above defeats.

**A flat tag pool was the obvious answer and was rejected on two counts.** It cannot express *which* destination — "Lisbon" and "Porto" sitting loose in one pool lose the question they answer — and nothing stops `lisbon`, `Lisbon` and `LIS` coexisting, which is a vocabulary that decays the week it is introduced. The alternative that survives is the one below: a declared axis with declared values. The lifecycle rules a flat pool would have needed anyway — renaming, merging, retiring, deleting a value that is in use — are owed either way, so the pool bought nothing in exchange for what it lost.

**Personal saved views were rejected too, and for a reason from outside this cluster.** A private vocabulary would make an agency's tagging invisible to everyone else, and outsourcing authoring to an agency working through the machine plane is the established path rather than a hypothetical one. A filing system only its author can see is not a filing system.

**One constraint may outrank all of it.** `list_content_records` (`backend/app/content/service.py:219-235`) ends in `.all()` with no limit, offset or filter, and so does every other list route the client reads. At the scale these questions describe that is not a performance note — the screen stops working, and it stops working after an adopter has copied an architecture that looked fine.

## Decision

**1. A facet is a declared axis with declared values, and filtering composes across facets.**
An adopter declares the axes they actually think in — *Audience: B2C · B2B*, *Destination: Lisbon · Porto*, *Type: product · company* — and a filter reads "Audience is B2B **and** Destination is Lisbon". Composition across axes is the property the flat pool could not provide, and it is the whole reason for the shape.

**System axes and manager axes share one model.** Per-channel readiness and `status` are further axes rather than a separate filtering mechanism, so there is one filter surface and one way to think about narrowing. This matters more than it sounds: a second mechanism for the system's own axes would be discovered by the first screen that needs to filter by both at once.

**Values are flat within a facet.** The nested option was not taken. The motivating IATA example *is* hierarchical, and the two reconcile by modelling Region, Country and Destination as three facets rather than one nested one. **The open consequence is stated rather than hidden:** a record tagged `Destination: Lisbon` does not satisfy `Country: Portugal` unless it carries that too, so either the tagger repeats themselves or something derives the broader value. That is unresolved and is owed before this is built.

**2. The word is "facet", with "facet values", in the API, the UI and the playbook.**
Every familiar alternative is already spoken for in this system. "Category" is [[ADR-080 — Human-governed Taxonomy Before AI Selection]]'s governed affinity taxonomy. "Label" collides with `ModuleVariable.label`, a form caption. "Attribute" collides with `RecipientDB.attributes`, free-form recipient data. "Tag" was the original suggestion and is rejected by its own connotation — it implies loose and free-form, which is precisely what point 1 decided against.

The user's reasoning generalises past this decision and is worth carrying as a rule: *"it's best to explain a new vocabulary than risking (system) confusion because of comfortability."* A word that needs explaining once is cheaper than a word that quietly means two things.

**3. Facets are declared per brand.**
This departs deliberately from the category precedent, and the departure is the point rather than an oversight. [[ADR-150 — Tenancy and Access Model]]'s 2026-09-15 addendum makes `CategoryDB` unbranded on the stated grounds that *"Content is per-brand; what a category MEANS is not."* That argument is about **affinity semantics** and does not carry to **findability**: a category carries meaning about a *recipient*, a facet carries meaning about *how a team works*. Two brands genuinely share what "Beach" means as an interest; they do not share how they file their work. An airline brand's axes (Destination, Cabin) and a hotel brand's (Property, Season) have no reason to be one list, and forcing a shared vocabulary would couple brands that [[ADR-150 — Tenancy and Access Model]] otherwise keeps apart.

The addendum that record needs is reported with this one rather than written into it, per this repository's rule that an Accepted record's Decision is never edited.

**4. Facets are shared and governed: an administrator declares them.**
Facets, their values, and the links from taggable things to values are a backend model, not a client convenience. With it come the lifecycle rules, which are part of the decision and not implementation detail: **renaming** a value, **merging** two, **retiring** one so it stops being offered without unfiling what already carries it, and what happens to tagged records when a value is **deleted**.

Its administration surface belongs in Settings, and **Settings has no router at all** — `backend/app/settings/` holds `service.py` and `db_models.py` and nothing that serves a route. So this work carries a dependency on a gap that exists for other reasons, and that dependency is real sequencing rather than a note.

**5. Facets apply to content and campaigns. Audience groups get search and paging only.**
The axes mean the same thing on both sides — a B2B campaign uses B2B content — so filing both by them is coherent, and a campaign's own facets are what let the content picker pre-narrow to *this campaign's* axes rather than to a channel alone. An audience group is **defined by its rules**; tagging it by topic would be describing a thing that already describes itself.

**The modelling consequence follows and is not optional: facets are not a column on the content table.** Two entity types means declared facets, their values, and links from taggable things to values. Whether that is one polymorphic link table or one per entity is an implementation choice; this repository's idiom favours the explicit version.

**6. A facet must never reach the decision engine, and the separation is structural rather than conventional.**
Facets are a separate model from `CategoryDB`, with no path into `candidate_filter`, no path into a decision slot's allowed- or excluded-category limits, and no path into `signal_contributions`. A manager cannot file a record along an axis that then quietly steers personalization, because there is nothing to file it into.

This is the one point that would be worthless as a guideline. "Do not put findability labels in categories" is advice; a manager under deadline is not reading advice, and the failure is silent when they do not. Two models means the mistake is unavailable rather than discouraged — and it is what keeps [[ADR-080 — Human-governed Taxonomy Before AI Selection]] true in fact rather than in intent, since a taxonomy anybody may quietly extend with non-affinity terms is no longer governed.

**7. Every list route accepts server-side filtering and pagination, and this is a precondition rather than an optimisation.**
The product must not assume a record count — a reference architecture is copied by adopters of very different sizes, so the API paginates and filters server-side including for the adopter who will never need it. Every facet filter, every readiness filter and every search from points 1 and 5 is a **query parameter the API must accept**, which makes this a shape decision about the API rather than a tuning exercise behind it.

**This reprices backlog item P3-02**, logged in the 2026-08-07 review as latent scaling destined for a `performance-notes.md` that was never created. At this posture it is a blocker on the core workflow, and it applies to campaigns, audiences, recipients and approvals as well as content. Schema and contract changes are cheap before a typed client exists and expensive afterwards, which is why this lands before the screens rather than under them.

**8. Cross-brand duplication reassigns facet values, and the mechanism already exists.**
`duplicate_campaign` (`backend/app/campaigns/duplication.py:127`) already takes a source and a target brand, already runs `KEEP` within a brand and `COPY` across one, and already reports the things that crossed verbatim as readable labels for a human to look at. Facet values the target brand does not have **join that list**, and the wizard allows reassignment rather than refusing the copy or silently dropping the tags. What the function cannot do today is accept a mapping, and that is the concrete gap this point opens.

## Consequences

### Positive

- **The manager's grouping exists as a first-class concept**, which it did not before, and the two screens being designed now — the content list and the campaign builder's picker — have something to narrow by other than an id.
- **ADR-080's taxonomy stays a taxonomy.** The pressure that would have degraded it — a manager needing an axis and reaching for the only vocabulary on offer — now has somewhere else to go, and point 6 means it cannot go to the wrong place by accident.
- **One filter surface covers system axes and manager axes**, so readiness and `status` are facets rather than a second narrowing mechanism nobody planned.
- **The vocabulary cannot decay into `lisbon` / `Lisbon` / `LIS`**, because values are declared before they are used and the lifecycle rules for changing them are part of the model rather than a later repair.
- **A campaign's own facets make the content picker much stronger than a channel filter alone** — building a B2B Lisbon campaign can show B2B Lisbon content first, which is the pre-narrowing the picker wants and could not otherwise express.
- **Server-side filtering and pagination arrive before the screens are finished rather than after**, which is the cheaper order, and they land across content, campaigns, audiences, recipients and approvals at once instead of one screen at a time.
- **An adopter's filing system is theirs.** Nothing here ships a vocabulary; the platform ships the axis mechanism and the adopter declares the axes, which is the same convention-based-extension posture the decision strategies and module templates already take.

### Negative

- **Setup before value, and it is the first thing an adopter meets.** Nobody can tag anything until an administrator has declared the axes, so the feature's opening state is an empty screen with a concept to learn. An adopter who skips it gets the same product they had before this record.
- **A multi-brand adopter redeclares common axes per brand**, and there is no sync — deliberately, since a synced copy is a copy that drifts, which is the same argument [[ADR-150 — Tenancy and Access Model]] uses to keep the category vocabulary global. The cost is real work, repeated, by the adopters who run the most brands. The first pilot customer runs around ten.
- **A cross-brand copy gains a reassignment step.** Duplication was a two-field operation; with per-brand facets it acquires a mapping the person doing it has to think about, on a path that previously did not stop to ask.
- **The tagging surface is built for two entity types**, so it is built twice unless it is shared from the start — and sharing it from the start is a design constraint on work nobody has scoped yet.
- **An adopter with two hundred records pays for machinery they do not need.** Pagination, filter parameters and the client code that drives them are all overhead at that size. Accepted because the alternative is that somebody hits a wall silently, having copied an architecture that looked fine at the size it was demonstrated in.
- **Phase 2's four list screens do not survive this.** They fetch everything and render it, which is the cost of having built them before the interview that decided this ran.
- **"Facet" is jargon, and every manager and playbook reader meets it once.** Accepted on the reasoning in point 2, but it is a real teaching cost paid by every adopter rather than once by this repository.
- **The repository has no glossary, and this is the first term that demonstrably needs one.** `docs/implementation/` defines no domain vocabulary at all, which was survivable while every term was borrowed from the industry. "Facet" is not, and neither, on inspection, are campaign, variant, module instance, decision slot, snapshot or signal contribution. This record creates an obligation it does not discharge.
- **Point 6 buys its guarantee with duplication.** Two models that both look like "a name attached to content" will sit beside each other in the schema, and the first reader of `backend/app/content/db_models.py` who does not know this record will ask why. The answer is good and it still costs a second model, a second admin surface and a second mental slot.

## Notes

- **The `## Status` line above is this record's whole claim to being safe to file: nothing here is superseded.** [[ADR-080 — Human-governed Taxonomy Before AI Selection]] is untouched and is *strengthened* by point 6; [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]'s category limits are untouched; [[ADR-150 — Tenancy and Access Model]] point 2's refusal of per-brand taxonomy is about the **affinity** taxonomy and is not contradicted by per-brand facets, which is exactly the distinction the addendum reported with this record has to make in that record's own words.
- **The addendum [[ADR-150 — Tenancy and Access Model]] needs is owed and is not applied here.** It is a dated `##` section on that record, per the addendum pattern this repository has used thirteen times, and it says why findability differs from affinity. Its text is reported alongside this record rather than written into it.
- **`CONTENT_FIELD_GROUPS` is a different concept and must not be conflated with this one.** That table (`backend/app/content/service.py:101-108`) declares which **content fields** belong to which channel — it is channel field grouping, a stopgap its own docstring asks to be replaced by reading the channel manifests, duplicated a second time at `backend/scripts/import_content_csv.py:33-41`. It groups *fields of one record*; facets group *records*. The resolution there is maintenance in favour of the manifests and needs no ADR; it is named here only because the two are easy to mistake for each other when both are described as "grouping content".
- **The hierarchy question is open and should be closed before this is built.** Point 1 takes flat values inside a facet, which leaves `Destination: Lisbon` not implying `Country: Portugal`. The cheap answers are that the tagger carries both, or that something derives the broader value from the narrower; neither was chosen, and choosing one after tagged data exists is more expensive than choosing it now.
- **Question 14's answer is recorded here because it is a decision not to build something.** "In feedback loop / waiting for feedback" is neither a facet nor a new lifecycle state: *not ready* is still being worked on, *ready* is the author is done, and *pending action* is an integration asserting readiness with a person yet to decide. No third state axis, nothing new built. If an adopter's editorial process genuinely has more stages, the cheap next step is a single-select `Workflow` facet — no lifecycle engine, each team naming its own stages — and that is a suggestion rather than a commitment.
- **Two concrete gaps this record opens, both already visible in `docs/backlog.md`:** `duplicate_campaign` cannot accept a facet-value mapping (point 8), and `GET /campaigns/decision-slots/{id}/resolutions` returns every row unpaginated on the fastest-growing table in the schema — the worst single instance of what point 7 rules against.
- **The decision log has no entry for the interview that produced this.** `docs/playbook-strategy.md` §5 ends at 2026-09-19, so Cluster 2's resolutions of 2026-09-21 live in [[Manager Workflow - design interview]] and in `docs/backlog.md` and nowhere in the log that records where decisions were made. That is a gap in the process rather than in this decision, and it is recorded so the next reader looking for the log entry behind this record knows why there is none.

## Related ADRs

### Depends On
- [[ADR-002 — API First Architecture]]
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]
