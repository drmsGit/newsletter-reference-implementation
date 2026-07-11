---
type: business-interview
status: open
topic:
  - architecture
  - business-strategy
  - review
  - baseline
created: 2026-07-05
modified: 2026-07-05
source:
  - claude-business-baseline-review-2026-07-05
---

# Business Interview Baseline

Scan of `docs/architecture/ADR/` (68 ADRs) and the backend implementation for decisions that are framed as neutral technical architecture but actually encode a specific business model, target customer, or market bet. This is a different lens than [[MOC - Interview Prep Baseline]], which asks "why this implementation approach" — this file asks "whose business assumptions are baked in, and would they survive a fork."

Grouping is by feature area, following the ADR numbering clusters. Each item answers the five standard questions. No fixes are proposed — this is a surfacing pass only.

The single most important cross-cutting finding: **`docs/playbook-strategy.md` contains the actual business reasoning behind several ADRs (target customer, monetization, why overrides exist, why AI is bounded) — but none of that reasoning is referenced from the ADRs themselves.** Anyone reading only `docs/architecture/ADR/` would have no way to discover it. Several items below point back to that file explicitly.

---

## Triage (2026-07-05)

Sorted against what's actually next, based on `docs/backlog.md` (🔴 To Do, priority order) and the phase sequence in `docs/playbook-strategy.md` §6. As of this pass: Phases 1A/1B/1C, 2A–2D, and 3A are shipped (git history 2026-07-03/04); the last two days have been the `/interview-review` pass, with three of four clusters cleared and **Snapshots/Rendering/Email Modules still open** — the literal next item in that queue. The next unbuilt roadmap phase is **3B (system-suggested audience)**, feeding into **3C (signal layer)**.

Each finding below is tagged inline at its heading. Summary:

### ✅ Resolved (2026-07-05) — business decision made this session

All 6 items flagged as blocking were talked through and resolved as business decisions in a dedicated session on 2026-07-05. Full narrative logged in `docs/playbook-strategy.md` → Decision Log → **"2026-07-05 — Business-Assumption Triage Resolutions."** One-line resolution each, detail inline at each finding below:

| Finding                                                                    | Resolution                                                                                                                                                                                                                                                                                                                                                                                                                        |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **B2** — Override layer / `OverrideEventDB` vs `module_data`               | Overrides (content *and* audience) exist for manager trust/ownership, by design. Stay low-friction everywhere; friction should trigger on scale/anomaly (a big, unexplained change to an already-trusted proposal), not on category (content vs. audience).                                                                                                                                                                       |
| **C4** — Content versioning / approval-gate assumption                     | A real approval/roles concept is wanted, not just a "publish" button. Lightweight stand-in belongs in the POC now; full roles/rights later; two-person approval should be an optional toggle so small teams can have one person do both.                                                                                                                                                                                          |
| **E2** — Hardcoded `content_score_weight`/`preference_score_weight` (10:1) | Direction confirmed: personalization ("what this person seems to like") should generally win by default. A distinct, named escape hatch — "guaranteed placement" — covers sales-must-show and partner-contract content instead of tuning the weighting formula for it. Exact magnitude (10:1 vs. something else) is a calibration detail for whoever builds the config-shape work, not a business question.                       |
| **J1** — Hardcoded `EVENT_PREFERENCE_DELTAS = {"click": 5.0}`              | Open, click, and conversion all count as positive interest; unsubscribe (incl. spam-complaint, which providers normalize to the same event) counts as a genuine *negative* signal. Ship sensible default weights, let companies retune once they trust the system.                                                                                                                                                                |
| **K1** — Audience Intelligence: permanent safeguard vs. shrinks over time  | The `playbook-strategy.md` §4 reading is the correct one — system proposes, trust grows over time. Manual bulk sends always need an explicit "go ahead"; automated/recurring cycles need it once at setup, with a "correct your proposal" adjustment path after.                                                                                                                                                                  |
| **L1** — MJML vs. actual 100%-raw-HTML templates                           | MJML decision stands, deliberately — module changes are rare (setup-time + occasional feature requests, branding refresh ~every 5 years), and "fix once, apply everywhere" (accessibility, Gmail quirks) justifies it even though the team doesn't know MJML yet. The manager composing an email never touches it either way — only the dev/design team does. Current all-raw-HTML state is a prioritization gap, not a reversal. |

Two new concepts surfaced during this pass that aren't decisions about existing findings — they're new ideas worth tracking on their own: **guaranteed placement / sponsored slots**, and a **pause/snooze subscription** feature. See [[#M. New Concepts Surfaced (2026-07-05)]] below and `docs/backlog.md`.

**2026-07-11 addendum:** **E1** resolved via `/business-review` — AI governance level becomes per-capability configuration (default = current ADR-080/081/082 posture), and AI capabilities become separate pluggable extension points (categorization, content generation, audience analysis), mirroring the provider-plugin-strategy pattern. Doesn't unblock building it now (still behind Phase 3C→3D), but the direction is set. **E3** also resolved — challenged and closed: no architecture rethink or policy toggle needed, the existing composition model (static content blocks) and strategy-plugin system already guarantee content by construction if a company wants that; only a small optional defensive safety-net check survives, logged to `docs/backlog.md`. **F1** also resolved — a minimal CRM-synced `consent_status` field + sync-drift log, checked at audience-resolution time (before decision/rendering run), driven by both a legal reason (GDPR "processing" is broader than just the final send) and a cost reason (avoid paying for AI/token-driven decisioning on recipients who'll never receive anything). **F2** also resolved — challenged and closed: the "context-specific, low-volume exempt" framing was too hedged; sender reputation is essentially universal for any real adopter of this campaign-scale architecture. Remaining gap is pure implementation sequencing (no real provider adapter yet), already tracked, now with a concrete bounce/complaint→consent-update reaction folded in given F1. **H1** also resolved — a real provider is required before public launch (not optional), sequenced late for cost reasons; outbound is close to easy (adapter pattern already established via `MockProvider`), inbound needs the not-yet-built adapter layer plus webhook signature/idempotency handling. Full narrative at §E1/§E3/§F1/§F2/§H1 below and `docs/playbook-strategy.md` → Decision Log → "2026-07-11 — Business-Assumption Triage Resolutions (continued)."

### 🟡 Self-resolving — deferred, revisit once the feature exists

Not implemented, and no near-term backlog/roadmap item builds them yet. Forcing an answer now would be guessing ahead of scope. Left open, not closed.

- **I1** — Automation layer accepted-but-unimplemented (ADR-090–095) — entire domain has no code and isn't on the Phase 1–4 roadmap at all.
- **G1** — Email-in-platform vs. identifiers-only ([[ADR-120 — CRM as Customer Source of Truth]] / [[ADR-054 — Use Internal Recipient Identifiers]] / [[ADR-126 — Maintain Local Recipient Projection]]) — resolved from "unsure" 2026-07-05: confirmed intended design is identifiers-only (internal + CRM/provider external IDs), `email` on `RecipientDB` today is a known deviation, not an open question. What's genuinely undecided — how simple personalization (salutation, "you're subscribed with this email" footer) gets its data without the platform owning email/name as a system of record — has no feature building it yet. Revisit once an example CRM integration is built (the planned proof-of-concept for how CRM ↔ newsletter platform ↔ provider hand off identity), since that's what will surface the real shape of the identifier/personalization boundary. See updated reasoning in §G1 below.

### ⚪ Non-blocking / cosmetic — batch for later

Stable, already-shipped, or pure positioning/naming — doesn't affect current or near-term work.

- **A1** — [[ADR-001 — Newsletter Architecture Boundaries]], CRM/consent/identity out-of-scope framing
- **A2** — [[ADR-125 — Define a Minimal Reference Architecture]], minimal path still requires CRM + Catalog
- **A3** — [[ADR-130 — POC Uses Modular Monolith, Target Architecture Supports Service Separation]], tech stack choice (already built, stable)
- **B1** — [[ADR-003 — Human-Guided Marketing, AI-Optimized Delivery]] philosophy (abstract, already stably reflected in shipped decision layer)
- **C1** — [[ADR-011 — Store Reusable Content Only]] threshold (editorial judgment call, stable)
- **C2** — [[ADR-012 — Content Records Represent Communication Units]] (foundational, shipped, stable)
- **C3** — `preferred_airport` / travel-vertical demo data (nullable field, naming/scope-clarity issue only)
- **D1** — [[ADR-020 — Campaign Equals Newsletter]] (foundational, shipped; journeys/programs aren't on the roadmap)

### ⚠️ Unsure — skip, needs your input

*(none remaining — G1 resolved to 🟡 deferred above, 2026-07-05)*

---

## A. Architecture Scope & Positioning

### A1. [[ADR-001 — Newsletter Architecture Boundaries]] — exclusion of CRM/CDP/consent/identity from core scope `⚪ non-blocking`

1. **Assumption:** The adopter already has (or will separately build/buy) a CRM, consent management platform, and identity resolution system. "Vendor-neutral" here means neutral among *email providers*, not neutral about whether the surrounding enterprise stack exists at all.
2. **Context-specific.** This is explicitly a positioning choice for a specific playbook/consulting product (see `docs/playbook-strategy.md` §1–2: target is agencies serving "German Mittelstand companies that have outgrown Mailchimp but don't want Salesforce Marketing Cloud"). A team without an existing CRM would need to build one first, silently, before any of this architecture is usable.
3. **Forking impact:** Blocks a solo-founder / small-SaaS fork outright — those teams often don't have a CRM and would treat "CRM as Customer Source of Truth" ([[ADR-120 — CRM as Customer Source of Truth]]) as extra unplanned scope, not a boundary decision.
4. **Documented:** Only as an architecture boundary ("Those systems may be connected, but they are outside the core architecture"). The *reason* — this is a project for teams that already run CRM-heavy tech stacks — lives only in `docs/playbook-strategy.md` §2, not in the ADR.
5. **What you'd need to explain:** That "vendor-neutral" is scoped to the delivery/ESP layer, not the whole martech stack, and that the target buyer (agency/Mittelstand) is assumed to already have CRM maturity — this project doesn't help you get there.

### A2. [[ADR-125 — Define a Minimal Reference Architecture]] — CRM → Content Catalog → Builder → Rendering → Provider as "the" minimal path `⚪ non-blocking`

1. **Assumption:** Even the "minimal" starting point still requires a CRM and a dedicated Content Catalog before a single email can be sent — there's no "just send an HTML email to a CSV list" tier below this.
2. **Context-specific.** A hobbyist, internal tool, or transactional-only sender would find even the "minimal" path over-engineered.
3. **Forking impact:** A fork for a much smaller use case (e.g. a single-person internal newsletter) would likely skip the Content Catalog and CRM steps entirely and go straight from a spreadsheet to a provider — which this ADR doesn't recognize as a valid "even more minimal" tier.
4. **Documented:** Yes, as an ADR — but framed purely as sequencing/adoption-curve, not as "this is still enterprise-shaped even at its smallest."
5. **What you'd need to explain:** The floor of this architecture assumes an organization, not an individual — "minimal" is relative to enterprise email marketing, not to email sending in general.

### A3. [[ADR-130 — POC Uses Modular Monolith, Target Architecture Supports Service Separation]] — specific tech stack (Python/FastAPI, React/TypeScript, PostgreSQL, Docker) `⚪ non-blocking`

1. **Assumption:** The team building/teaching from this reference implementation is comfortable hiring or already staffed for Python + React — a stack chosen for teachability and the author's own delivery capacity (freelance consulting, per `docs/playbook-strategy.md` §1), not derived from the architecture itself.
2. **Context-specific**, though the ADR presents it as a project decision rather than a business one. Nothing in the domain model requires Python/React specifically — the ADR itself says AI must be "interchangeable" and vendor-neutral, but the implementation stack is not treated with the same neutrality.
3. **Forking impact:** A Java/.NET or Node-only shop would naturally reimplement in their own stack (the ADR anticipates this — "modular monolith is a deployment decision, not a rejection of service separation") — low blocking risk, but the *choice itself* (why Python+React, not e.g. Node end-to-end) is a consulting-practicality decision dressed as an architecture one.
4. **Documented** as a decision, but the "why this stack" reasoning (workshop delivery, own skill set, hiring pool for the target agencies) is not in the ADR — only inferable from `docs/playbook-strategy.md`.
5. **What you'd need to explain:** This stack pick is about what the author (and target agencies) can staff and teach, not a technical requirement of the reference architecture.

---

## B. Human/AI Division of Labor & the Override Layer

### B1. [[ADR-003 — Human-Guided Marketing, AI-Optimized Delivery]] — automation is scoped to "operational" tasks, strategy stays human `⚪ non-blocking`

1. **Assumption:** Marketing teams at the target customer *want* to keep strategic ownership and would resist a fully autonomous system — this is a market-acceptance bet, not a technical constraint. Nothing about AI capability limits "AI ranks candidates" to being safer than "AI plans campaigns"; the limit is adoption psychology.
2. **Context-specific.** For a different buyer (e.g. a performance-marketing team that explicitly wants autonomous optimization, or a low-touch newsletter with no dedicated marketer), this constraint is pure friction with no benefit.
3. **Forking impact:** A fork targeting full automation (e.g. a lifecycle/product-marketing SaaS) would need to *remove* governance gates like [[ADR-082 — AI May Recommend but Not Publish]], not just extend them — this is a philosophical floor, not a default that's easy to raise.
4. **Documented** as an ADR, with the "why" (avoid marketer displacement, preserve strategic ownership) stated in the Context/Notes sections — this is one of the better-documented business assumptions in the set. Status is still "Proposed," not "Accepted."
5. **What you'd need to explain:** This is explicitly a stance on the automation-adoption fear ("AI will replace me"), aimed at winning trust with marketing teams — not a claim that more automation would be worse.

### B2. [[ADR-040 — Introduce Override Layer]] / [[ADR-041 — Override Precedence]] and the `overrides` module (`backend/app/overrides/service.py`) — overrides exist because of manager psychology, not data integrity `✅ resolved 2026-07-05`

**Resolution (2026-07-05):** Confirmed — overrides exist for manager trust/ownership, and that holds for *both* content and audience overrides equally (audience-proposal adjustments are the same mechanism, not a separate one). Friction should stay low across the board, on purpose — the trust-building feedback loop only works if people actually use the override and then get shown the comparison, so blocking them defeats the point. The one real friction trigger isn't category (content vs. audience) as originally designed — it's **scale/anomaly**: a manager drastically changing an *already-trusted* proposal (e.g. inflating a segment to 200k recipients) is the risk case worth a "why," not routine editing. On the shadow-variant question (an open, ADR-conflicting item in `docs/backlog.md`'s Needs-ADR section) — this resolves differently depending on override type, and only partially. **Audience overrides:** no shadow variant needed when a manager adds people beyond the system's proposal, or accepts it outright — everyone in question actually gets sent to, so real per-recipient engagement gives a natural comparison group with no parallel system-built send required. **But** when a manager *deletes/excludes* people the system proposed, those excluded recipients never receive anything — their hypothetical engagement is unknowable without actually sending to them, the same problem content overrides have (below). Flagged as a real gap but expected to be rare in practice (deletion happens far less than addition), so noted rather than solved. **Content overrides:** genuinely still open. If a manager replaces the system's chosen content, the system's rejected pick is never sent to anyone — there's no real engagement data to validate "the system's pick would have done just as well" without an actual shadow send (or equivalent), so the [[ADR-021 — Variants Are Human Created Versions]] conflict this raises is **not resolved** by this session. Full narrative in `docs/playbook-strategy.md` Decision Log, 2026-07-05.

1. **Assumption:** Marketing managers need to feel ownership over content details even when their edits don't materially change outcomes — the override layer exists to manage a *feeling*, not to solve a technical requirement. This reasoning is stated almost verbatim in `docs/playbook-strategy.md` §5 ("Most manual tweaks... don't materially affect outcomes — but the psychological need to act is real and must be designed for") but the ADRs present overrides as a purely editorial/content-governance mechanism.
2. **Context-specific**, and unusually explicit about it once you find the strategy doc — this is a bet about a specific customer psychology (Mittelstand managers who "want to do the work themselves, not less of it"), not a universal need.
3. **Forking impact:** A fork targeting a fully automated / no-human-in-the-loop use case (e.g. a pure recommendation engine) would likely rip out the entire override layer rather than reduce it — the layer's existence *is* the assumption.
4. **Not documented as a business decision anywhere near the ADR.** [[ADR-040 — Introduce Override Layer]]'s stated context is purely "editors need campaign-specific adjustments" — a content-governance justification. The actual strategic reasoning (trust-building, tiered friction by stakes, "let the system decide is the default with a visible escape hatch") lives only in `docs/playbook-strategy.md` §5 and is not linked from the ADR at all.
5. **What you'd need to explain:** That `OverrideEventDB` (`backend/app/overrides/db_models.py`) is being designed as a trust-building/audit artifact for a sales narrative ("you overrode 4% of sends; in 70% of those the system's pick performed equally well") — a future analytics/consulting deliverable — not just a content-diff mechanism. None of that commercial intent is visible from the schema or the ADR.

---

## C. Content Governance & Domain Modeling

### C1. [[ADR-011 — Store Reusable Content Only]] — the "realistic need to use it more than once" threshold `⚪ non-blocking`

1. **Assumption:** There's an editorial team with the judgment and authority to gatekeep the catalog, and enough send volume that catalog pollution is a real risk worth the governance overhead.
2. **Context-specific.** A low-volume sender (a handful of campaigns a year) would find this gatekeeping step pure ceremony — the catalog will never grow large enough to need curation.
3. **Forking impact:** A small team would naturally skip the reuse-judgment step and store everything in the catalog, effectively ignoring this ADR without realizing they're deviating from it.
4. **Documented** as an ADR, with the trade-off (editor judgment burden) stated in Consequences — reasonably transparent for this one.
5. **What you'd need to explain:** This rule assumes catalog scale as a *problem to prevent*, not a *goal to reach* — teams with small catalogs shouldn't feel obligated to enforce it.

### C2. [[ADR-012 — Content Records Represent Communication Units]] — content records are "reusable communication units," not generic objects `⚪ non-blocking`

1. **Assumption:** The business has a stable catalog of "things to talk about" (destinations, products, offers) that map cleanly to *editorial angles*, and that AI/automation is trustworthy enough to be handed structured, human-curated units rather than raw product/CMS data. This is a content-marketing mental model, not a transactional or product-catalog one.
2. **Context-specific** to editorial/lifecycle marketing use cases. A transactional or e-commerce-catalog-driven sender (where content = live product feed) would find "communication unit" an awkward, extra translation layer over data that already exists elsewhere.
3. **Forking impact:** A fork wired to a live product feed (e-commerce abandoned cart, price-drop alerts) would likely bypass the Content Catalog's editorial model and go straight from feed to render — quietly violating [[ADR-010 — Newsletter Content Source of Truth]] rather than extending it.
4. **Documented** in the ADR itself, reasonably well ("A different topic, angle or seasonal message should usually become a new record").
5. **What you'd need to explain:** This model assumes editorial curation is a feature, not overhead — it's built for brand/lifecycle marketing, not for real-time catalog-driven commerce.

### C3. Demo/reference data and the travel-industry vertical baked into a "vendor-neutral" architecture `⚪ non-blocking`

Concrete evidence: `create_demo_content_if_empty()` in `backend/app/content/service.py:76-113` seeds "Mallorca Beach Walk," "Rome City Weekend," "Tenerife Nature Escape" under categories "Beach," "City," "Nature." More significantly, `RecipientDB` (`backend/app/recipients/db_models.py:6-22`) has a first-class column `preferred_airport`, alongside `language` — not a generic `attributes` JSON field, an actual named column.

1. **Assumption:** The reference implementation, despite being pitched as a domain-agnostic "vendor-neutral reference architecture," is really modeled on a **travel/tourism newsletter business** (the "Condor" source referenced in ADR frontmatter, e.g. `source: condor-reference-system`). Categories, taxonomy shape, and even a core recipient field are travel-specific, not illustrative placeholders.
2. **Context-specific**, but currently implemented as if universal — `preferred_airport` is a real schema column in the "minimal recipient model" ([[ADR-121 — Minimal Recipient Model]] lists only recipientId/email/consent/country/language as minimal+recommended fields — `preferred_airport` isn't among them, yet it's hardcoded into the base table anyway).
3. **Forking impact:** Blocks nothing functionally (it's nullable), but it is a strong, immediate signal to anyone forking this for a non-travel vertical that the "reference" implementation is actually a rebrand of one company's system, undermining the "vendor/domain neutral" pitch on first read of the schema.
4. **Not documented as a decision anywhere.** There is no ADR that says "recipient model includes a travel-specific field" or explains why. It's discoverable only by reading `db_models.py`.
5. **What you'd need to explain:** That this column (and the demo taxonomy) are leftover from the airline/travel case study this architecture was extracted from, and should be treated as an example of a *business-specific extension field* (which [[ADR-121 — Minimal Recipient Model]] explicitly allows) rather than as part of the reference model proper.

### C4. [[ADR-128 — Version Content for Auditability and Restoration]] — publish/approve/release as the version-triggering event `✅ resolved 2026-07-05`

**Resolution (2026-07-05):** Confirmed — a real approval/roles concept is wanted, this isn't a one-person-operation assumption to relax. Full roles-and-rights (who can build, who can approve, who can hit send) is planned future work and out of scope for right now, but a **lightweight stand-in belongs in the POC already** — explicitly because prospective clients will ask for it. Two-person approval ("maker-checker") should be an **optional toggle**, off by default or easily disabled, so a small team can have one person both build and approve without the system blocking them.

1. **Assumption:** The organization has (or will build) an approval workflow with meaningful gates between draft and sendable content. The ADR explicitly "does not define the full approval workflow" but assumes one exists conceptually.
2. **Context-specific** to teams with editorial review/legal-compliance steps. A one-person operation has no "approval" distinct from "I'm done editing."
3. **Forking impact:** In the current implementation there is no approval workflow at all — `ContentRecordDB.status` defaults to `"active"` (`backend/app/content/db_models.py:12`) with no draft/review states enforced anywhere, and `update_content_record` (`backend/app/content/service.py:17-25`) mutates the live record with no version bump. A solo-operator fork wouldn't need to change anything to diverge from this ADR's intent — it's already unenforced.
4. **Documented** as an ADR describing the intended future workflow, but the gap between "documented intent" and "current code has no gating at all" is not flagged anywhere except tangentially in [[Interview Prep - Content, Campaigns, Audience]] (a technical-implementation review, not this business lens).
5. **What you'd need to explain:** That the versioning model is designed around an approval process that doesn't exist yet in code — adopters without an approval workflow shouldn't expect versioning to give them audit safety today.

---

## D. Campaign Model

### D1. [[ADR-020 — Campaign Equals Newsletter]] — one campaign = one send-worthy unit `⚪ non-blocking`

1. **Assumption:** The organization's mental model of "campaign" is a single email, and multi-step journeys (reactivation flows, Black Friday programs) are the exception to be handled via metadata grouping, not the norm. This matches a **newsletter/broadcast marketing team**, not a lifecycle/CRM-automation team where multi-step journeys are the primary unit of work.
2. **Context-specific.** A product-led or lifecycle-marketing org (welcome series, onboarding drips) would find "campaign = one email" backwards — for them, the journey *is* the campaign, and an individual email is a step.
3. **Forking impact:** A lifecycle-marketing fork would likely need to introduce a parent "Program"/"Journey" object above Campaign — something this ADR explicitly defers ("through metadata or grouping, not as mandatory parent objects") rather than models directly. Not a hard block, but a real missing layer for that use case.
4. **Documented** well as an ADR, including the tension ("organizations may use the term campaign differently").
5. **What you'd need to explain:** This is a terminology and mental-model bet toward newsletter/broadcast marketing, not lifecycle/journey marketing — the latter would need an additional layer this architecture treats as optional.

---

## E. Decision Layer & AI Governance

### E1. [[ADR-080 — Human-governed Taxonomy Before AI Selection]] / [[ADR-081 — AI Ranks Within Governed Candidate Sets]] — AI never chooses outside a human-built taxonomy `✅ resolved 2026-07-11`

**Resolution (2026-07-11):** ADR-080/081/082 aren't really one governance switch — they're three separable gates: (1) does AI need a human-built taxonomy to work within, (2) does AI only rank within a given candidate set or can it also expand it, (3) does AI's output need human approval before it takes effect. Resolution: **AI governance level becomes configuration (per-capability gates), not a fixed architectural stance** — the current ADR-080/081/082 posture (human-governed taxonomy, human-approved output) becomes the *default* configuration, matching the target Mittelstand buyer persona, but a company with fewer people and more trust in AI can loosen individual gates via config without forking the code. Separately: **AI capabilities (content categorization, content generation, audience/recipient analysis) become distinct pluggable extension points, not one monolithic "the AI."** These are genuinely different ML problems best served by different models/approaches. This directly reuses the pattern already established for the provider layer (provider-plugin-strategy decision) — keep the architecture model-agnostic, ship one worked reference implementation per capability for the playbook/proof-of-concept, let real adopters bring their own model. The "marketers can just export the catalog and use an external AI tool manually" fallback stays true regardless, but that's the *ungoverned* pattern pillar #1 of the strategy exists to replace, not a reason to skip building the governed version. Doesn't unblock building this now — still gated behind Phase 3C (signal layer) → 3D (AI-based audience selection) — but changes what gets built when that phase arrives: a per-capability guard-config layer over pluggable AI extension points, not a single fixed AI philosophy baked into the architecture.

1. **Assumption:** The organization has staff willing and able to build and maintain a category taxonomy, scoring rules, and category relations *before* any AI value is realized — a governance-first bet that trades faster time-to-value for control. This assumes the buyer (per `docs/playbook-strategy.md` §2, Mittelstand orgs burned by "black box" systems) values explainability enough to accept the upfront taxonomy cost.
2. **Context-specific.** A growth-stage company optimizing for velocity over control (or one with no dedicated content ops team) would find this taxonomy-first requirement a significant barrier to any AI feature at all.
3. **Forking impact:** A fork aimed at "AI picks the best content, full stop" (common in growth/performance-marketing tooling) would need to bypass the taxonomy gate entirely, not extend it — this is a hard governance floor, matching the explicit "I can't see what and why the system is doing it" pain point named in `docs/playbook-strategy.md` §3, which doesn't apply to every buyer.
4. **Documented** as an ADR with clear rationale ("business control," "less black-box behavior"). The *customer story* behind why this matters this much (prior bad experience with Salesforce-style black boxes) is only in `docs/playbook-strategy.md`, not referenced from the ADR.
5. **What you'd need to explain:** This isn't a generic AI-safety best practice — it's a direct response to a specific client complaint pattern about opaque systems, aimed at winning trust with a customer base that has been burned before.

### E2. `RecipientTopScoreStrategy` hardcoded weighting (`backend/app/decision/strategies/recipient_top_score.py:9-12`) — `content_score_weight: 1`, `preference_score_weight: 10` `✅ resolved 2026-07-05`

**Resolution (2026-07-05):** Direction confirmed — by default, personalization should generally win ("what this person seems to like"), consistent with the trust-building philosophy (see K1/B2). What was missing is now named: a distinct **"guaranteed placement"** mechanism for cases where personalization should be overridden entirely — sales pushing a must-show item, or partner content with a contractual minimum-placement guarantee. This is deliberately *not* a weighting-formula tweak (it doesn't compete on score, it's simply guaranteed) and not quite the existing override mechanism either (it's usually set by sales/contracts, not the manager building the email) — see [[#M. New Concepts Surfaced (2026-07-05)]]. The exact 10:1 magnitude itself is left as an implementation calibration detail, not a business decision — whoever builds the declared `strategy_config` shape can set a sensible number.

1. **Assumption:** Recipient-level preference signal should count 10x more than editorially-assigned content score by default — an opinionated business tuning choice (personalization-over-editorial-priority) presented as a neutral code default (`DEFAULT_CONFIG`).
2. **Context-specific**, and the code already half-recognizes this — weights are overridable via `slot.strategy_config` — but the *default* ratio is a real business choice (favor personalization strongly over editorial ranking) with no stated rationale anywhere.
3. **Forking impact:** Wouldn't block a fork (it's overridable per-slot), but anyone not aware of the 10:1 default would silently inherit a strong personalization-over-editorial bias without ever having decided that trade-off themselves.
4. **Not documented as a decision anywhere** — no ADR discusses the relative weighting philosophy between editorial score and preference score; it's discoverable only by reading the constant in code.
5. **What you'd need to explain:** Why 10:1 and not, say, 2:1 or 1:1 — there's no written rationale, so this reads as an arbitrary tuning value promoted to a silent default that shapes every send using this strategy.

### E3. [[ADR-086 — Decision Slots Fail Gracefully]] — "If no meaningful newsletter content remains, the email must not be sent" `✅ resolved 2026-07-11`

**Resolution (2026-07-11):** No architectural rethink or company-level policy toggle needed — challenged and closed. Two reasons: (1) the "cadence matters more than relevance" case is narrower than it first reads — it only really applies to pure news-style newsletters, and even there, those categories almost always have enough content, and non-engagement itself is useful preference signal rather than a pure loss. (2) More importantly, **"guarantee something always sends" is already achievable today with zero new architecture** — a `ModuleInstanceDB` bound directly to a `content_record_id` (not a decision slot) always renders regardless of what any decision slot resolves to, so a marketer just includes one statically-assigned content block alongside any dynamic modules. A fully-empty email can only happen if *every* module in a variant is decision-slot-driven and *all* resolve to nothing simultaneously — a composition the marketer chose, not something the platform forces. Even in that all-dynamic case, a company wanting guaranteed content can write their own decision strategy that never returns `None` (e.g. "best available match, even at low confidence") — exactly what the strategy-plugin system already exists for. The only surviving piece is a small, optional **defensive safety net**: refuse/alert if a fully rendered email ends up with literally zero content modules, purely to catch accidental misconfiguration, not as a business-policy decision — logged to `docs/backlog.md` as a minor Feature, not treated as resolving a deep strategy question because it isn't one.

1. **Assumption:** Under-sending (skipping a send entirely) is always safer than sending a less-personalized or generic fallback email — a brand-safety-over-reach bet. This assumes the cost of "recipient got nothing this cycle" is lower than the cost of "recipient got an irrelevant/empty-feeling email."
2. **Context-specific.** For a business where consistent cadence matters more than per-send relevance (e.g. a weekly digest audience expects *something* every week), silently skipping sends could itself be the worse outcome — churn from inconsistency vs. churn from irrelevance is a business trade-off, not a technical one.
3. **Forking impact:** A fork prioritizing send-cadence reliability would need to introduce a generic/static fallback path this ADR explicitly treats as optional ("Fallback content is optional") rather than mandatory — a philosophy reversal, not an extension.
4. **Documented** as an ADR, but framed as risk-avoidance ("reduces manual preparation effort," "avoids irrelevant fallback content") without acknowledging the opposite trade-off (missed cadence) as a real cost for some businesses.
5. **What you'd need to explain:** That "don't send anything is fine" is itself a market bet about the recipient relationship (occasional/curated communication) that doesn't hold for every newsletter program.

---

## F. Consent, Privacy & Compliance

### F1. [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]] and [[ADR-122 — Minimal Consent Model Required]] vs. the actual `recipients` implementation `✅ resolved 2026-07-11`

**Resolution (2026-07-11):** Resolved — a minimal, CRM-synced consent gate, not a CRM replacement. `RecipientDB` gets a flat `consent_status` field (opted-in / opted-out / pending), sourced from the CRM, not authored here — already permitted by [[ADR-126 — Maintain Local Recipient Projection]], which explicitly lists "communication preferences" as an allowed Recipient Projection field. Plus a **consent-sync log** (audit trail of consent status over time), specifically to detect drift between the CRM's actual state and this platform's cached copy if a sync ever fails or lags — "CRM says no, we still say yes" needs to be a detectable, not silent, failure mode. Reason this can't just be "trust the CRM↔provider connection": some providers (e.g. Selligent) ignore opt-outs entirely for API-triggered sends, treating them as transactional — relying on the provider to enforce consent would mean building a provider-specific workaround, exactly what the provider-abstraction layer (ADR-101/105) exists to avoid. This platform is the only place left that can reliably close that gate. **Filtering point: at audience-resolution time, before decision/rendering run at all — not a late gate right before the provider call.** Two independent reasons converge on this: (1) legal — GDPR's definition of "processing" (Article 4(2)) is broad enough that running decision-engine scoring against a non-consenting recipient's data could itself be a processing activity requiring its own legal basis, not just the final send (this needs real legal review for a production deployment, not just architectural reasoning); (2) **cost — the sharper business reason.** As decisioning increasingly routes through paid AI models or automation platforms (e.g. n8n), running a decision pass for recipients who'll never actually receive anything is not just wasted compute, it's wasted spend, and that only gets worse as AI/token costs rise. A related, genuinely separate idea surfaced here — the decision engine giving cost/token feedback before running an AI-driven batch — is tracked as its own new concept, not folded into this resolution (see New Concepts).

Concrete evidence: `RecipientDB` (`backend/app/recipients/db_models.py:6-22`) has no consent, marketing-eligibility, or communication-type field of any kind. `send_send_instance()` (`backend/app/delivery/service.py:111-172`) iterates every `DeliveryExecutionDB` tied to a send instance and calls `provider.send(...)` unconditionally — there is no consent or eligibility check anywhere in the send path.

1. **Assumption:** Consent/compliance enforcement is a "later phase" concern that can be deferred without changing the architecture — reflected in ADR-004 still being status "Proposed" (not "Accepted") a month after most delivery/provider ADRs were accepted, and in ADR-122's confident "must" language ("Only recipients eligible for the selected communication type may enter delivery processes") having zero corresponding enforcement in code.
2. **This is presented as universal/mandatory in the ADR text** ("must," "shall," "first-class") but is treated as context-specific/deferrable in practice — a real mismatch between stated and revealed priority. For a GDPR-bound EU business (the explicit target market per `docs/playbook-strategy.md` §2), this gap is not a minor implementation detail — it's a regulatory blocker before any real send.
3. **Forking impact:** Doesn't block a fork technically (there's nothing to override — it's just absent), but anyone adopting this reference implementation for a real send, believing the ADRs describe current behavior, would be exposed to real compliance risk. The ADR reads as "solved," the code says "not started."
4. **Documented as an ADR requirement, but the gap between requirement and implementation is not documented anywhere in the ADR set.** It is flagged in [[MOC - Interview Prep Baseline]] ("No consent/marketing-opt-out gate exists at send time... a known, accepted gap for the POC") — but that framing (POC scope note) is a different lens than "this is a stated business promise the code doesn't keep."
5. **What you'd need to explain:** That every consent/privacy ADR describes target-state intent, not current guarantees — treating ADR status "Proposed" as a real signal (most of these two are still Proposed, not Accepted) rather than assuming acceptance-adjacent ADRs are all equally implemented.

### F2. [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]] — deliverability/reputation as a universal concern `✅ resolved 2026-07-11`

**Resolution (2026-07-11):** Challenged and closed — the original "context-specific, doesn't apply to low-volume/internal use" framing was too hedged. Domain/IP sender reputation is typically *shared* across everything sent from that domain unless traffic is deliberately isolated onto separate subdomains, so marketing complaints can block transactional mail on a shared domain; and even fully isolated transactional-only sending isn't safe from this, since recipients marking those as spam degrades that stream's own reputation regardless of the sender's own classification. More fundamentally: this architecture already assumes campaign-scale sending (ADR-125's minimal path requires a CRM + Content Catalog before a single email goes out) — a genuinely tiny/personal-scale sender wouldn't be using this system at all, they'd call a transactional API directly. So for any real adopter of *this* architecture, ADR-106's "must" framing holds essentially universally, not as a narrow commercial-marketing bet. What's genuinely still deferred is pure implementation sequencing — no real provider adapter exists yet to receive bounce/complaint webhooks at all — already tracked in `docs/backlog.md`. **New, concrete addition given F1 is now resolved:** a bounce/complaint event should (1) update the recipient's `consent_status` (revoke/mark opted-out) and relay back to the CRM if there's no direct CRM↔provider webhook, since this platform is the only place positioned to notice; and (2) separately feed the Insight layer as a content-quality signal ("this content triggered a lot of complaints") — a distinct, analytics-flavored use of the same event, not the same action as the consent update. Folded into the existing provider-adapter-layer Feature in `docs/backlog.md`.

1. **Assumption:** Every adopter sends at commercial volume where sender reputation and inbox placement are a real, ongoing risk — true for broadcast/marketing email, less true for low-volume transactional or internal use.
2. **Context-specific**, though phrased as an unconditional requirement for "every production-ready provider integration."
3. **Forking impact:** A low-volume or internal-tool fork would find this requirement irrelevant overhead — there's no reputation risk to manage at that scale — but the ADR doesn't carve out that case.
4. **Documented** as an ADR with a clear (if narrow) rationale.
5. **What you'd need to explain:** This requirement assumes commercial marketing-email economics (sender reputation as a shared, scarce resource) that don't apply to every use of "send an email to many people."

---

## G. CRM & Recipient Identity

### G1. [[ADR-120 — CRM as Customer Source of Truth]] and [[ADR-054 — Use Internal Recipient Identifiers]] — email addresses should live in CRM/provider systems, not the platform `🟡 deferred`

**Update 2026-07-05 (confirmed with the author, resolved from "unsure"):** The intended design is not ambiguous — it's identifiers-only by deliberate data-protection choice. The platform should store only the internal recipient identifier plus the external identifier(s) from the CRM and, where it differs, the provider — never the email address itself. `RecipientDB.email` (`backend/app/recipients/db_models.py:11`) existing as a plain required column today is a known, acknowledged deviation from that design, not an open interpretive question. What *is* still genuinely open: simple personalization (salutation by first/last name, a "you're subscribed with this email" footer line) needs *some* access to email/name data at render or send time, and it isn't yet decided whether that means a narrow, purpose-limited projection field, a just-in-time CRM lookup at send time, or something else — this is explicitly parked until an example CRM integration is built (the planned proof-of-concept for how CRM ↔ newsletter platform ↔ provider identity hand-off actually works end to end), since that's the point at which the real shape of the identifier/personalization boundary will become concrete rather than hypothetical.

1. **Assumption:** A privacy-maximalist stance (minimize PII surface inside the newsletter platform) is worth the added integration complexity of identifier mapping — a defensible default for the GDPR-bound target market, but a real cost for teams without a CRM to delegate email storage to.
2. **Context-specific**, but the ADRs (and [[ADR-126 — Maintain Local Recipient Projection]]) present it as architecturally correct rather than as a deliberate trade favoring one regulatory environment (EU/GDPR) over ease of standalone operation.
3. **Forking impact:** A fork with no CRM (common for smaller SaaS/indie use) would have nowhere to "push" the email address to and would likely just store it directly on `RecipientDB` (as the current implementation already does — `email` is a plain required column, not a reference) — quietly diverging from the stated principle from day one.
4. **Documented** extensively across several ADRs (004, 054, 120, 121, 126) — one of the better-covered areas — but always as architecture-correctness reasoning, never explicitly named as "this is a GDPR-market bet, and teams outside that regulatory context can reasonably choose differently."
5. **What you'd need to explain:** That minimizing PII inside the platform is a compliance-driven default tuned for EU/Mittelstand adopters, and that the current code (`RecipientDB.email` stored directly, `backend/app/recipients/db_models.py:11`) already doesn't fully live up to the "email stays in CRM" principle — the design intent is identifiers-only; the schema hasn't caught up, and personalization (salutation, subscribed-email footer) is the specific open question waiting on the example CRM integration to resolve concretely.

---

## H. Provider Layer

### H1. [[ADR-100 — Provider Layer as Send and Feedback Adapter]] / [[ADR-101 — Provider Capabilities Are Explicit]] / [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]] — provider independence and swap-ability `✅ resolved 2026-07-11`

**Resolution (2026-07-11):** A real provider is required before public launch — not optional, not context-specific — since "provider independence, no lock-in" is a core pitch claim that's currently untested against any real vendor. Deliberately sequenced late in POC development (after the remaining frontend work), specifically because it costs real money (paid ESP account, sending-domain setup). Confirmed asymmetry while discussing scope: the **outbound (send) side is close to easy** — `DeliveryProvider` and `MockProvider` already establish the pattern, a real adapter is mostly a small HTTP client against the ESP's send API. The **inbound (webhook/engagement) side is more involved** — the adapter contract for this doesn't exist at all yet (`providers/adapters/` is still an empty file), and beyond data-shape translation it needs webhook signature/authenticity verification, retry/idempotency handling, and a stable public HTTPS endpoint (partly infrastructure, not just code). Both sides need the adapter layer built first (see the provider-adapter-layer Feature in `docs/backlog.md`). **POC-specific addition:** will use an existing personal/business domain for the POC rather than register a fresh sending domain purely for this — accepting that domain warmup happens on that domain regardless. Open follow-up, not yet decided: consider a dedicated fresh domain instead, since a clean sending domain will be needed for this architecture's own public playbook/marketing anyway, and warmup has real calendar lead-time independent of code — worth starting that clock earlier than the code integration itself, if a fresh domain is the eventual choice.

1. **Assumption:** Adopters will realistically want or need to switch email providers over the system's lifetime, and paying the integration-abstraction cost up front is worth it. This is explicitly the pitch to the target buyer — `docs/playbook-strategy.md` §2 names "Salesforce Marketing Cloud's cost and lock-in" as the exact pain this is positioned against.
2. **Context-specific** to buyers who have been burned by vendor lock-in (the named Mittelstand persona). A team happy with a single provider forever would find the abstraction layer (capability tables, adapter interfaces, canonical event normalization) pure overhead relative to calling the provider's SDK directly.
3. **Forking impact:** Not blocking, but the *only* implemented adapter is `MockProvider` (`backend/app/delivery/providers/mock.py` — 20 lines, returns a fake `provider_message_id` and always succeeds). The entire provider-independence promise is currently untested against any real vendor (Brevo/Resend/SES are named in [[ADR-129 — Correlate Provider Events to Delivery Executions]]'s examples but none are implemented). A fork evaluating this architecture has no evidence the abstraction actually holds up against a real provider's quirks.
4. **Documented** as ADRs with clear, unusually well-articulated rationale — but the vendor-lock-in *sales narrative* behind why this matters this much is only in `docs/playbook-strategy.md`, and the "we've only ever tested this against a mock" caveat isn't documented anywhere.
5. **What you'd need to explain:** That "provider independence" is currently a design promise, not a proven one — and that the business case for caring about it at all (lock-in fear from a specific customer segment) should inform how much abstraction effort a forker actually needs.

---

## I. Automation Layer

### I1. [[ADR-090 — Automation References Campaigns, Not Decisions]] through [[ADR-095 — Use Send Instances for Technical Execution Tracking]] — six "Accepted" ADRs, zero implementation `🟡 deferred`

Concrete evidence: `backend/app/automation/` does not exist as a directory (compare to `content/`, `campaigns/`, `decision/`, `delivery/`, `insight/`, `overrides/`, `providers/`, `recipients/`, `rendering/`, `snapshots/` — all present with code). All six Automation ADRs (090–095) carry `status: accepted`.

1. **Assumption:** "Accepted" ADR status is being used to mean "this is the agreed direction" rather than "this is built" — automation is treated as a genuinely optional extension layer (consistent with [[ADR-125 — Define a Minimal Reference Architecture]]'s framing of Automation as an "optional extension"), so its absence isn't treated as a gap worth flagging anywhere.
2. **This is a documentation-convention assumption, not a domain one** — but it's a business-relevant one: a prospective adopter or workshop attendee skimming ADR statuses would reasonably assume "Accepted" ADRs describe working software, matching how ADRs read elsewhere in this repo (most accepted ADRs *do* have corresponding code).
3. **Forking impact:** Doesn't block a fork technically (there's nothing to conflict with), but it does mean anyone using ADR status as a proxy for "is this real" will be misled specifically in this cluster.
4. **Not documented anywhere** — no ADR or note flags that the Automation domain is accepted-on-paper-only. `docs/playbook-strategy.md`'s "What exists today (baseline)" list (§Roadmap) confirms Automation isn't mentioned among implemented modules, but doesn't call out the ADR-status mismatch explicitly either.
5. **What you'd need to explain:** That ADR status in this repo tracks *design agreement*, not *build status* — and that the Automation cluster specifically is 100% design, 0% code, despite reading identically to fully-implemented clusters like Delivery or Content.

---

## J. Insight / Signals Layer

### J1. `EVENT_PREFERENCE_DELTAS = {"click": 5.0}` (`backend/app/insight/service.py:12-14`) — only clicks move preference scores `✅ resolved 2026-07-05`

**Resolution (2026-07-05):** Confirmed — open, click, and conversion should all count as positive interest signals (conversion availability depends on the adopting company's own tracking capability). Also confirmed, and new: **unsubscribe should count as a genuine negative signal**, in service of "better to stop emailing someone who's checked out than keep pushing" — unsubscribe and spam-complaint are treated as the same event (providers normalize both to "unsubscribe" already). Relative magnitudes should ship as sensible defaults, fully retunable once a company trusts the system (same pattern as E2). A related idea surfaced but not decided as scope: offering a "pause/snooze" (temporary unsubscribe, re-approach later) instead of only a hard unsubscribe — see [[#M. New Concepts Surfaced (2026-07-05)]].

1. **Assumption:** Click is the only engagement signal worth trusting for preference learning; opens, bounces, unsubscribes, and conversions carry no preference-update weight at all, and 5.0 (vs. category assignment score, itself scaled ~0–10 per `create_demo_content_if_empty`) is the "right" magnitude for a click's influence.
2. **Context-specific business tuning presented as infrastructure.** [[ADR-112 — Signals Use Time-Based Decay]] and [[ADR-113 — Separate Operational and Historical Signals]] are both "Accepted," but there is no decay logic anywhere in `insight/service.py`, and no signal-type distinction beyond this one hardcoded dict — the ADRs describe a signal *philosophy* the code hasn't caught up to, similar to the Automation gap in §I1.
3. **Forking impact:** A fork wanting opens or conversions to influence personalization would need to design the entire weighting scheme from scratch — there's no extension point (no registry, unlike the Decision Strategy pattern), just a dict to edit directly.
4. **Not documented as a decision anywhere** — no ADR states "only clicks count" or explains the 5.0 magnitude; it's discoverable only in code.
5. **What you'd need to explain:** That this single constant currently *is* the entire personalization learning signal for the whole platform — despite the Insight layer's ADRs (110–113) describing a much richer signal model (recipient/content/composition/audience signals, decay, operational vs. historical split) that doesn't exist in code yet.

---

## K. Audience / Segmentation

### K1. [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]] vs. the stated design philosophy in `docs/playbook-strategy.md` §4 `✅ resolved 2026-07-05`

**Resolution (2026-07-05):** The `playbook-strategy.md` §4 reading is confirmed correct — system proposes, trust grows over time, not a permanent co-equal check. Concrete workflow: manager builds the email/cycle, system proposes the audience, manager either trusts and sends, or adjusts (adds people manually, and/or removes some of the proposed group — partial removal is fine even when the proposal came from multiple combined criteria). One-off/manual bulk sends always require an explicit "go ahead" click. Automated/recurring cycles (e.g. reactivation) only need that approval once, at setup, with a "correct your proposal" adjustment path for later rather than re-approving every cycle. Audience adjustments feed the same trust-building override mechanism as B2 — see there for the friction model and the shadow-variant question (resolved for additions/full-acceptance, still open for deletions and for content overrides).

1. **Assumption:** The ADR frames "AI suggests, CRM/human stays authoritative" as a neutral governance safeguard. But `docs/playbook-strategy.md` §4 states the actual intended default rather differently: *"'intelligence decides who needs what' is the default; managers get bounded guidance/override options rather than full manual control"* — i.e., the strategic intent is for the system to *drive* segmentation over time, with human authority as a fallback/trust-building mechanism, not a permanent co-equal check.
2. **Context-specific**, and there's a real tension between the two framings worth surfacing: the ADR reads as "humans stay in charge," the strategy doc reads as "humans stay in charge *for now, as a transitional trust-building measure*." Someone building against the ADR alone would design a different long-term UX than someone building against the strategy doc.
3. **Forking impact:** Not blocking, but a fork's roadmap would diverge significantly depending on which framing it inherits — "AI proposes, CRM stays boss forever" vs. "AI proposes, gradually earns full control." The ADR doesn't signal that the second reading is the actual intended trajectory.
4. **Documented, but in two places with materially different long-term implications**, and the ADR does not reference or reconcile with the strategy doc's framing.
5. **What you'd need to explain:** The ADR is a snapshot of the *current* governance safeguard; the actual product bet (per playbook-strategy.md) is that this safeguard's *prominence should shrink over time* as trust is earned — that trajectory isn't visible from the ADR alone.

---

## L. Rendering & Templates

### L1. [[ADR-131 — Email Module Templates Use MJML as Source Format]] — MJML compiled in the Node/React frontend, Python backend never touches it `✅ resolved 2026-07-05`

**Resolution (2026-07-05):** MJML stands, and deliberately — this isn't a stale decision the implementation quietly abandoned. New modules get built rarely (mostly once at initial setup, otherwise only when marketing requests a new feature) and full branding changes happen roughly once every five years, so the "fix once (e.g. an accessibility or Gmail-rendering quirk), apply everywhere" benefit justifies the tooling investment even though the team doesn't currently know MJML — the learning curve is a one-time cost against years of easier maintenance. Confirmed this also can't create the frontend-lock-in problem originally flagged: the marketing manager composing an actual email never touches MJML either way (raw HTML or MJML) — only the developer/technically-skilled-designer team who builds the reusable modules does, and that's the intended audience for MJML from the start. The current all-raw-HTML state is a prioritization gap (hasn't been urgent yet), not a reversal of the decision.

1. **Assumption:** A React/Node frontend will always be present and in the loop at send-preparation time — the ADR states this outright ("Python backend cannot independently re-render a snapshot without... a call to a Node compilation step"). This forecloses a backend-only or non-React integration (e.g. a headless API-only adopter, or a team using a different frontend framework) from ever compiling templates without standing up the specific Node toolchain this repo uses.
2. **Context-specific** to teams adopting the full reference stack (React frontend + Python backend) together. An adopter who only wants the Python backend (e.g. to integrate into an existing non-React product) inherits a hard dependency on a frontend they may not want.
3. **Forking impact:** Meaningfully blocks a backend-only fork — MJML compilation isn't optional plumbing, it's the only path from authored template to sendable HTML in this design. A forker would need to either adopt the Node toolchain anyway or replace MJML with something the Python backend can compile natively (defeating the ADR's stated benefit of the declarative authoring format).
4. **Documented** as an ADR, and unusually candid about the trade-off in its own Consequences section ("the Python backend cannot independently re-render a snapshot without a pre-compiled HTML artifact"). This is one of the most self-aware ADRs in the set.
5. **What you'd need to explain:** That choosing MJML wasn't just a template-format decision — it structurally requires a Node/React presence in any deployment of this architecture, which is a bigger commitment than "which templating language do we like."

---

## M. New Concepts Surfaced

Not resolutions of existing findings — new ideas that came out of discussion, worth tracking as their own concepts rather than folding into an existing mechanism. Logged to `docs/backlog.md` for future scoping.

### M1. Guaranteed placement / sponsored slots

A content slot that sits *outside* personalization ranking entirely — sales flags an item as "will show no matter what" (usually one-off, last-minute), or a partner contract guarantees minimum placement on an ongoing basis. Distinct from the override mechanism (B2) because the trigger and the owner are different: overrides are a manager reacting to one send; a guaranteed placement is closer to an ad-slot/sponsorship guarantee, potentially owned by sales or a partner contract rather than the person building the email. Not yet designed — surfaced while resolving E2 (personalization-vs-brand-control weighting).

### M2. Pause/snooze subscription

Instead of only a hard unsubscribe, offer a temporary "pause" — stop sending for a while, then re-approach later — as a softer alternative for someone who's disengaged but not necessarily gone for good. Surfaced while resolving J1 (unsubscribe as a negative interest signal); explicitly flagged by the author as likely more than POC scope, not a near-term build.

### M3. Cost/token feedback before running AI-driven decisioning

As decision-engine strategies increasingly route through paid AI models or automation platforms (e.g. n8n), give an estimate of cost/token usage *before* actually running a decision batch — not just gating on consent (F1), which avoids running decisioning for recipients who'll never receive anything, but proactively surfacing the expected cost for the recipients who *will*. Genuinely separate from F1's consent gate — this applies even to fully-consenting audiences if a company wants cost visibility before committing to a large AI-driven run. Not yet designed; ties into the pluggable AI-capability extension points from E1's resolution and the not-yet-built Phase 3C/3D AI work. Surfaced while resolving F1 (2026-07-11).

---

## Summary Table (highest-leverage findings)

| Area | Finding | ADR reads as | Actually is |
|---|---|---|---|
| Overrides ([[ADR-040 — Introduce Override Layer]]) | Content-governance mechanism | A trust-building/sales narrative artifact for a specific customer psychology (`playbook-strategy.md` §5) |
| Consent ([[ADR-122 — Minimal Consent Model Required]]) | Mandatory ("must") | Zero enforcement in code; ADR-004 still "Proposed" |
| Provider independence (100/101/105) | Proven, neutral abstraction | Only tested against `MockProvider`; real-vendor swap-ability unverified |
| Automation (090–095) | Accepted, implemented like other clusters | 100% design, 0% code — `backend/app/automation/` doesn't exist |
| Audience intelligence ([[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]) | Permanent human-authority safeguard | Intended as a *shrinking* safeguard over time, per `playbook-strategy.md` §4 |
| Recipient model (`preferred_airport`) | Domain-neutral reference schema | Travel-vertical field baked into the "minimal" recipient model |
| Recipient scoring weights (`recipient_top_score.py`) | Neutral default config | Undiscussed 10:1 personalization-over-editorial business bet |

## Related

- [[MOC - Interview Prep Baseline]] — technical/implementation-lens counterpart to this document
- `docs/playbook-strategy.md` — the actual business/product strategy source most of these findings trace back to, and where resolved findings' full narrative gets logged (Decision Log)
- `docs/backlog.md` — tactical fix queue (not the right place for the items above, which are classification, not action items)

## How to use this
Use the `/business-review` command to work through the 🟡 deferred / ⚠️ unsure items in the Triage section above, one at a time, rather than ad hoc. Resolved findings get a narrative resolution note here plus a mirrored entry in `docs/playbook-strategy.md`'s Decision Log — this file is the classification/audit trail, that file is the durable business-decision record.
