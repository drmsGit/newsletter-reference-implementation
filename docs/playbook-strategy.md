# Playbook & Architecture Strategy — Working Notes

**Purpose:** Running log of strategic decisions about the playbook/architecture project (positioning, monetization, design philosophy). Not an ADR — this is business/product strategy, not a technical architecture decision. Update as thinking evolves.

---

## 1. Project Vision

- Core output: a **playbook** (free website and/or ebook) teaching a vendor-neutral email marketing architecture.
- Explicit stance: **teach, don't sell a finished product.** Code ships "usable as-is, but meant to be tailored" — not a polished SaaS.
- Possible productized layer on top: a "fancy version" sold as a starter package (e.g. €199) for people who want a head start without building from the ADRs themselves.
- Monetization ladder (not required to work immediately):
  1. Free playbook/architecture → reach, community, credibility
  2. Productized starter package → low-friction entry revenue
  3. Workshops & consulting → main revenue path, especially for agencies
  4. Long-term hope: existing freelance consulting work gradually shifts into this project rather than needing to be a separate income stream from day one

## 2. Target Audience

- **Primary (economic buyer in practice):** agencies/freelancers serving mid-market clients — they have the technical capacity to act on the architecture and would attend workshops.
- **Secondary (the actual end customer / story):** German Mittelstand (KMU) companies that have outgrown Mailchimp but don't want Salesforce Marketing Cloud's cost and lock-in.
- Validation signal: already has real clients (as freelance consultant) and at least one agency expressing interest in this direction.

## 3. Core Pillars (client pain → architectural answer)

Derived from recurring client complaints, mostly from companies using Salesforce:

| Client pain | Architectural answer | Key ADRs |
|---|---|---|
| "I can't see what and why the system is doing it" | Explainable decision resolution, snapshot reconstruction, signals instead of black-box ML | ADR-085, ADR-062, ADR-110–113 |
| "Anything complex (dynamic content, AI) needs developers" | Modular, convention-based extension points — drop a file following a contract, the system picks it up (plugin-style, not no-code) | ADR-040/041 (override/guideline layer), decision strategy modules |
| "Standards don't fit my workflow, I build workarounds everywhere" | Architecture built on principles, not a fixed tech stack — IT can implement in whatever language/stack fits, as long as the contracts are honored | Cross-cutting; modular monolith approach |

This mapping is the spine of the playbook: every chapter should open with the client quote, then the principle, then the ADR, then code, then the deliberate extension point ("Ausblick"), then a real case study.

## 4. Design Philosophy: Modularity = Convention-Based Extension, Not No-Code

Clarified 2026-06-24: the "I need developers" pain point is NOT solved by removing developers entirely. It's solved by making extension mechanical and well-contracted:

- **Templates/email rendering:** drop a new `2col_product.html` file with declared variables into a folder, it shows up in the frontend. Design language is extensible by convention.
- **Decision engine:** one file per strategy (`top_score.py`, `recipient_top_score.py`, etc.). BI teams already using Python/BigQuery for things like CLV can contribute new strategies as new files.
- **Audience/segmentation:** "intelligence decides who needs what" is the default; managers get bounded guidance/override options rather than full manual control.

**Open priority flagged:** for the decision-engine extension point to be safely "bring your own strategy," the plugin contract needs to be explicit and enforced — input/output shape, required graceful-failure behavior (return `None`, never raise — currently violates ADR-086), and how confidence/explainability is reported back. This is documentation + interface hardening work, not new features.

## 5. Decision Log

### 2026-06-24 — Override/Guideline Layer Philosophy

**Context:** ADR-040/041 (override layer) was flagged in the drift report as architecturally weak (overrides crammed into a JSON blob, no clean separation from structural config). This layer turns out to be doing double duty — it's both the content-override mechanism AND the human-governance guardrail over AI-driven segmentation. Decided to design this deliberately rather than patch it.

**Idealized position:** in a perfect world, there would be no override function at all — just clear guidance fed into the AI/algorithm so the output is inherently approvable and within guidelines. Trust the system, don't let humans hand-tweak it.

**Pragmatic reality:** this is unrealistic for the target market.
- Most marketing managers want to do the work themselves, not less of it. Only a minority are happy to "let the system decide" and accept imperfect pixels.
- Most manual tweaks marketing managers make are on details that don't materially affect outcomes — but the *psychological need to act* is real and must be designed for, not dismissed.
- Segmentation has the same dynamic: most companies choose audiences based on what they *believe* is right, not what the data says is right. True data-driven segmentation-acceptance is the minority case, not the norm — even though it's architecturally the "correct" default.
- A solution that says "you cannot override anything, not even a headline" will not be adopted by this audience, regardless of architectural correctness.

**Resolution (2026-06-24):** Don't frame this as "override vs. no override" — separate the override's *cost* from its *visibility*, and make every override feed back into the system as data. This turns the override layer into the engine of the core sales narrative: **managers do less and less over time, and trust the system more, because the system proves itself to them.**

Design principles adopted:

1. **Overrides are a "pin," not a rewrite.** A manager can override *which* content record fills a slot, or force-include a segment/recipient — but the underlying rendering/personalization logic stays system-governed. They get control over the thing they care about without breaking the structure/content separation the architecture depends on (ADR-013, ADR-031).

2. **Every override is logged with what the system would have chosen instead.** Not punitive — this is the foundation of the trust-building feedback loop. Goal: be able to show a client "you overrode 4% of sends; in 70% of those, the system's original pick performed equally well." This is the proof-point that justifies trusting the system more over time, and it doubles as the ADR-085 explainability audit trail for free.

3. **Friction is tiered by stakes.** Headline/CTA-level content overrides: cheap, one click, no friction (lets people keep the feeling of ownership where it doesn't hurt anything). Segmentation/audience overrides: slightly more friction (optional reason field, a visible "this differs from system recommendation" flag) — because that's the one place a wrong manual call can cause real damage (wrong audience, compliance, brand risk).

4. **"Let the system decide" is the default with a visible escape hatch, not a wall.** Pitch is never "you cannot." It's "the system proposes, you can always override anything — and over time we'll show you how often that was worth doing." This is the specific narrative that lands with Mittelstand decision-makers: smooth transfer of ownership from manager to system, never a forced jump.

**Data model implication:** instead of cramming overrides into `ModuleInstanceDB.module_data` (current state, flagged in drift report against ADR-040/041), introduce a dedicated override/event record: what was overridden, the system's original recommendation (content/segment it would have picked), who did it, optional reason, and downstream performance outcome once available. Small, well-scoped model — not a big lift — but it's the artifact that produces the proof-points the consulting pitch depends on.

**Related future concept (not yet to be designed, just captured):** a "co-occurrence recommendation" feature — e.g. "swap this content for that one; tracking shows these two perform well together when used in the same email." This is a natural extension of the same trust-building loop: the system doesn't just defend its own picks passively, it proactively surfaces opportunities while a manager is still actively building. Park this for later, but it belongs to the same design family as the override/recommendation loop above.

**Status:** design direction settled. Next concrete step: sketch the override-event data model (fields, relations to existing models).

### 2026-07-05 — Business-Assumption Triage Resolutions

**Context:** A business-strategy review (`docs/business-interview-baseline.md`) flagged 21 places where the ADRs/implementation quietly encode a business assumption rather than a neutral technical choice. Six of them were judged urgent enough to resolve now, ahead of near-term implementation work (override redesign, content versioning, decision-strategy config, the signal layer, system-suggested audience, and the still-open Snapshots/Rendering/Email-Modules review). Resolved in a dedicated business-decider-style conversation, not a technical one — decisions below, implementation left to the relevant technical sessions.

1. **Audience proposals are part of the same trust-building override mechanism as content — but the "do we need a shadow variant" question resolves differently for each, and only partially.** Workflow: manager builds the email/cycle → system proposes the audience → manager either trusts-and-sends, or adjusts (adds people manually and/or removes some of the proposed group, including partial removal when multiple criteria produced the proposal). **Audience overrides via addition (or full acceptance):** everyone in question actually gets sent to, and because engagement is tracked per recipient, the adjusted cohorts within one real send serve as their own natural comparison group — no system-built "shadow variant" is needed here. **Audience overrides via deletion/exclusion:** people the system proposed but the manager removed never get sent anything, so there's no real engagement data for them — the same open problem content overrides have, below. Flagged as a real gap but expected to be rare in practice (deletion happens far less than addition), so it's noted, not solved, for now. **Content overrides:** unresolved. If a manager replaces the system's chosen content, the system's rejected pick is never sent to anyone — there's no way to get real engagement data proving "the system's pick would have done just as well" without an actual shadow send (or equivalent), so the conflict this raises with [[ADR-021 — Variants Are Human Created Versions]] (variants are always human-created) remains genuinely open — not resolved by this session. Approval flow, separately: manual bulk sends always need an explicit "go ahead"; automated/recurring cycles need that approval once, at setup, with a "correct your proposal" adjustment path afterward rather than re-approving every cycle. Underlying reason this matters at all: left unchecked, marketing defaults to "this is interesting for everyone" nine times out of ten — as content volume grows, that becomes recipient fatigue. The system's job is to prove that a narrower, genuinely-interested audience outperforms "send to everyone," so managers adopt narrower targeting willingly rather than being forced into it.

2. **Overrides (content and audience both) should stay as low-friction as possible, on purpose — not tiered by category.** The original design (2026-06-24 entry above) tiered friction by category: content edits cheap, audience/segment edits given more friction "because that's the one place a wrong manual call can cause real damage." That's superseded: friction should be low across the board, because the trust-building feedback loop (showing managers "here's what would've happened") only works if people actually use the override freely. The real friction trigger is **scale/anomaly**, not category — a manager drastically overriding an *already-trusted* system proposal (e.g. inflating a 500-person segment to 200k) is the actual risk case worth a "why are you doing this" prompt, regardless of whether it's a content or audience override.

3. **MJML remains the right call for email module templates, confirmed deliberately.** New modules are built rarely — mostly once at initial setup, then only when marketing requests a genuinely new feature; full branding refreshes happen roughly once every five years. The team currently doesn't know MJML, but "fix once (accessibility updates, Gmail rendering quirks), apply everywhere" against years of low module churn justifies the one-time learning cost. Also confirmed: this never creates a frontend-lock-in problem for the *marketing manager* composing an email, because that person never touches MJML (or raw HTML) either way — only the developer/technically-skilled-designer team building reusable modules does, which was always MJML's intended audience. The current 100%-raw-HTML implementation state reflects prioritization (hasn't been urgent), not a reversal.

4. **A lightweight approval/roles stand-in belongs in the POC now; full roles-and-rights is later.** Confirmed a real approval concept is wanted (not just a one-click "publish") — prospective clients will ask for this regardless. Two-person approval ("maker-checker") should be an **optional toggle**, so a small team can have one person both build and approve without the system forcing a second reviewer that doesn't exist on their team.

5. **Personalization should generally win by default, with a named escape hatch for commercial priority.** Default: "what this person seems to like." For cases where personalization should be overridden entirely — sales pushing a last-minute must-show item, or partner content with a contractual minimum-placement guarantee — a **new, distinct concept** is needed rather than tuning the personalization-weighting formula: a "guaranteed placement" slot that sits outside personalization ranking. This is deliberately not the same mechanism as a manager override (different trigger — a business/contractual guarantee, not a one-off judgment call; often a different owner — sales/partnerships, not the person building the email). Not yet designed; captured in `docs/business-interview-baseline.md` §M1.

6. **Engagement signals: open, click, and conversion all count as positive interest; unsubscribe counts as a genuine negative signal.** Conversion tracking availability depends on the adopting company's own capability; open and click are always available (click weighted more heavily, open treated as the least reliable signal). Unsubscribe and spam-complaint are treated as the same event (providers already normalize both to "unsubscribe"), and are deliberately scored as *negative* interest — philosophy is "better to stop emailing someone who's checked out than keep pushing," not squeeze every last send out of a disengaged recipient. Related idea surfaced, explicitly flagged as likely beyond POC scope: a "pause/snooze" option (temporarily stop, re-approach later) as a softer alternative to a hard unsubscribe — captured in `docs/business-interview-baseline.md` §M2. Signal weighting itself: ship sensible defaults, let companies retune once they trust the system and understand the intelligence behind it — same pattern as the decision-strategy weighting question above.

**New concepts captured, not yet scoped:** guaranteed placement / sponsored slots (item 5); pause/snooze subscription (item 6). Both logged to `docs/backlog.md` for future design work, not near-term builds.

**Status:** five of six business assumptions resolved as decisions; the sixth (item 1, override-outcome validation) is only partially resolved — settled for audience overrides via addition, still open for audience deletions and, more importantly, for content overrides, where the shadow-variant/ADR-021 conflict remains unresolved and needs its own follow-up decision. Implementation (override schema redesign, content versioning/approval gate, decision-strategy config shape, signal layer, system-suggested audience flow, MJML compiler wiring) is separate follow-up work, tracked in `docs/backlog.md` and the ongoing `/interview-review` pass — not done in this session.

### 2026-07-11 — Business-Assumption Triage Resolutions (continued)

**Context:** All four technical `/interview-review` clusters are now fully cleared, unblocking a return to `docs/business-interview-baseline.md`'s remaining 🟡 deferred findings via the new `/business-review` command.

1. **AI governance level becomes per-capability configuration, not a fixed architectural stance ([[ADR-080 — Human-governed Taxonomy Before AI Selection]] / [[ADR-081 — AI Ranks Within Governed Candidate Sets]] / [[ADR-082 — AI May Recommend but Not Publish]]).** These three ADRs are really three separable gates — (1) does AI need a human-built taxonomy to work within, (2) does AI only rank within a given candidate set or can it also expand it, (3) does AI's output need human approval before it takes effect. Rather than one fixed governance philosophy, each gate becomes a config setting. The current ADR-080/081/082 posture (human-governed, human-approved) is the **default**, matching the target Mittelstand buyer persona — but a company with fewer people and more trust in AI can loosen individual gates via config, without forking the code. Underlying tension this resolves: different customer segments genuinely want different amounts of AI autonomy (more trust/fewer people vs. more control/more risk-aversion about miscommunication), and an open-source architecture meant to be extended shouldn't force one posture on everyone.

2. **AI capabilities become separate pluggable extension points — content categorization, content generation, and audience/recipient analysis are not one monolithic "the AI."** These are genuinely different ML problems best served by different models/approaches. This directly reuses the pattern already established for the provider layer (see provider-plugin-strategy decision) — keep the architecture model-agnostic, ship one worked reference implementation per capability for the playbook/proof-of-concept, and let real adopters bring their own model rather than maintaining a library of AI-vendor integrations. The always-available fallback ("a marketer can just export the catalog and use an external AI tool manually") stays true regardless of what's built, but that's exactly the *ungoverned* pattern pillar #1 of the strategy ("I can't see what and why the system is doing it") exists to replace — it's the fallback, not a reason to skip building the governed version.

**Status:** Directional decision only — doesn't unblock building this now, since it's still gated behind Phase 3C (signal layer) → 3D (AI-based audience selection). Changes *what* gets built when that phase arrives: a per-capability guard-config layer over pluggable AI extension points, not a single fixed AI philosophy baked into the architecture. Full classification detail in `docs/business-interview-baseline.md` §E1.

3. **"Email must not be sent if no meaningful content remains" ([[ADR-086 — Decision Slots Fail Gracefully]]) needs no architecture rethink or company-level policy toggle — challenged and closed.** The "cadence matters more than relevance" counter-case is narrower than it first reads (mostly just pure news-style newsletters, which almost always have enough content anyway, and non-engagement is itself useful preference signal, not pure loss). More importantly: **the composition model already guarantees content by construction if a company wants it** — a `ModuleInstanceDB` bound directly to a `content_record_id` (not a decision slot) always renders regardless of decision-slot outcomes, so including one static content block alongside dynamic modules is a zero-new-architecture guarantee. A fully-empty email requires every module in a variant to be decision-slot-driven *and* all resolve to nothing — a composition the marketer chose. Even then, a company can write its own decision strategy that never returns `None`, using the existing strategy-plugin system. Only surviving item: a small, optional defensive safety-net check (refuse/alert if a rendered email ends up with zero content modules, purely to catch accidental misconfiguration) — logged to `docs/backlog.md`, not treated as a business-policy question because it isn't one. Full classification detail in `docs/business-interview-baseline.md` §E3.

4. **A minimal, CRM-synced consent gate belongs in this architecture — not a CRM replacement, but not fully deferrable to "CRM ↔ provider" either ([[ADR-004 — Privacy Operations as a First-Class Architectural Concern]] / [[ADR-122 — Minimal Consent Model Required]]).** `RecipientDB` gets a flat `consent_status` field sourced from the CRM (already permitted — [[ADR-126 — Maintain Local Recipient Projection]] explicitly lists "communication preferences" as an allowed projection field), plus a consent-sync log to detect drift if CRM↔platform sync ever fails ("CRM says no, platform still says yes" needs to be detectable, not silent). Reason this can't just be "trust the CRM↔provider connection": some providers (e.g. Selligent) ignore opt-outs entirely on API-triggered sends, treating them as transactional — relying on the provider to enforce consent means a provider-specific workaround, exactly what the provider-abstraction layer exists to avoid. **Filtering happens at audience-resolution time, before decision/rendering run at all**, for two converging reasons: legally, GDPR's definition of "processing" is broad enough that running decision-engine scoring against a non-consenting recipient's data could itself require its own legal basis, not just the final send (needs real legal review for production, this is architectural reasoning, not legal advice); and — the sharper business reason — as decisioning increasingly routes through paid AI models or automation platforms (e.g. n8n), running a decision pass for people who'll never receive anything is wasted spend, not just wasted compute, and that only gets worse as AI/token costs rise. A related, separate idea — the decision engine giving cost/token feedback before running an AI-driven batch — is tracked as its own new concept (`docs/business-interview-baseline.md` §M3), not folded into this decision. Full classification detail in `docs/business-interview-baseline.md` §F1.

5. **Sender reputation ([[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]) is essentially universal for this architecture's real adopters, not a narrow commercial-marketing bet — the original "context-specific, low-volume/internal use exempt" framing was too hedged.** Domain/IP reputation is typically shared across everything sent from that domain unless deliberately isolated onto separate subdomains, so marketing complaints can block transactional mail on a shared domain; and even isolated transactional-only sending isn't safe, since recipients marking those as spam degrades that stream's own reputation regardless of the sender's own classification. More fundamentally, this architecture already assumes campaign-scale sending (ADR-125's minimal path requires a CRM + Content Catalog before a single email goes out) — a genuinely tiny/personal-scale sender wouldn't be using this system, they'd call a transactional API directly. What's genuinely still deferred is pure implementation sequencing (no real provider adapter exists yet to receive bounce/complaint webhooks), already tracked. **New, concrete addition now that F1 (consent) is resolved:** a bounce/complaint event should update the recipient's `consent_status` and relay back to the CRM if there's no direct CRM↔provider webhook, and separately feed the Insight layer as a content-quality signal — two distinct reactions to the same event, folded into the existing provider-adapter-layer Feature in `docs/backlog.md`. Full classification detail in `docs/business-interview-baseline.md` §F2.

6. **A real provider integration is required before public launch — not optional, not context-specific ([[ADR-100 — Provider Layer as Send and Feedback Adapter]] / [[ADR-101 — Provider Capabilities Are Explicit]] / [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]]).** "Provider independence, no vendor lock-in" is a core pitch claim and is currently untested against any real vendor (only `MockProvider` exists). Deliberately sequenced late in POC development — after remaining frontend work — specifically because it costs real money (paid ESP account, sending-domain setup). Asymmetry confirmed: outbound (send) is close to easy, the adapter pattern already exists via `DeliveryProvider`/`MockProvider`; inbound (webhook/engagement) is more involved — that adapter contract doesn't exist at all yet, and needs webhook signature verification, retry/idempotency handling, and a stable public HTTPS endpoint beyond just data-shape translation. POC will use an existing domain rather than register a fresh one purely for this, accepting warmup happens on that domain — open follow-up on whether a dedicated fresh domain makes more sense given it'll be needed for the architecture's own public playbook/marketing anyway (domain warmup has real calendar lead-time independent of code). Full classification detail in `docs/business-interview-baseline.md` §H1.

---

## 6. Roadmap

*Strategic, phase-level sequencing (Phase 1-4). For the granular, prioritized queue of specific bugs/features decided while working through the interview-prep review, see `docs/backlog.md` instead.*

### What exists today (baseline)
- Backend: FastAPI modular monolith with modules for campaigns, content, decision engine, delivery, insight, providers, recipients, rendering, snapshots
- Decision strategies: `top_score`, `recipient_top_score` — with a registry + base class already in place (good plugin foundation)
- Frontend: server-side Jinja HTML templates — read-only views exist for campaigns, content, decisions, delivery, recipients, categories, dashboard
- Recipients: basic model + event/preference tracking, no audience groups
- Everything is created via API or direct SQL — no editing UI exists

---

### Phase 1 — Architecture Contracts (foundation, unblocks everything else)

These are decisions and small implementations that other phases depend on. Mostly design + light code, no big features.

**1A. Plugin contract: decision strategies**
The registry + base class already exist — good. What's missing: an enforced contract on graceful failure (strategies must return `None`, never raise — ADR-086) and explainability (strategies must return a `reason` and `score` alongside the resolved content — ADR-085). Every new `.py` strategy file drops into `decision/strategies/` and auto-registers. Document the contract clearly — this is the "BI hands you a file and it works" promise.

**1B. Plugin contract: HTML email templates** ✓
Template format decided: MJML (MIT, self-hosted, no GDPR exposure). Templates are authored in MJML by designers, compiled to HTML in the Node/React frontend layer at send/preview time. Python backend receives compiled HTML — never invokes MJML directly. Raw HTML permitted as escape hatch. Manifest format (frontmatter in file) implemented. See ADR-131.

**1C. Override-event data model**
New DB table: `OverrideEventDB` — records what was overridden, the system's original recommendation, who did it, optional reason, timestamp. Relations to `ModuleInstanceDB` (content overrides) and eventually `AudienceGroupDB` (segmentation overrides). This is the trust-building audit trail. Small, well-scoped, do it before building any editing UI so overrides are logged from day one.

---

### Phase 2 — Editing Frontends (make it demonstrable to a manager)

All views currently exist as read-only Jinja templates. Extend them into forms. Priority order:

**2A. Content management** — create/edit content records and versions. Foundational: nothing else has real data without this.

**2B. Campaign + variant builder** — create campaigns, variants, module instances, assign content or decision slots to modules. This is the core "email building" flow.

**2C. Send preparation** — create send instances, assign audience (manual for now), trigger snapshot + send. This is the end-to-end demo path.

**2D. Decision slot configuration** — pick a strategy from dropdown (auto-populated from strategy registry), set parameters, preview what it would resolve. Depends on Phase 1A.

---

### Phase 3 — Audience / Segmentation Layer (the AI story starts here)

Currently: recipients exist, events and preferences are tracked, nothing else.

**3A. Manual audience groups** — create a named group, add recipients by criteria (tag, preference, explicit list). This is the "manager wants control" surface. Needed before any send can be meaningfully targeted.

**3B. System-suggested audience** — based on existing preference/event data, the system proposes a recipient set for a given campaign/variant. Manager sees the suggestion, can override (logged via 1C). This is the first visible expression of the trust-building loop.

**3C. Signal layer (ADR-110–113)** — transform raw engagement events into typed, time-decaying signals. Prerequisite for any serious AI-based segmentation. This is the biggest architectural gap in the codebase right now, and also the most complex. Design before building.

**3D. AI-based audience selection** — uses signals (not raw events) to propose recipient sets. Depends on 3C.

---

### Phase 4 — Playbook Production (parallel track, can start anytime)

Not blocked by code — can be worked on alongside other phases.

**4A. Decide playbook structure and communication style** — who is the reader per chapter (manager, developer, BI), what does each chapter promise, how are "Ausblick" extension points presented so they read as intentional, not unfinished.

**4B. Map 2–3 real client cases to the three pillars** — which client illustrates "I can't see what the system does," which illustrates "I need devs for everything," which illustrates "standards don't fit my workflow."

**4C. Write and publish** — website and/or ebook.

---

### Drift report items (address during relevant phases, not separately)

| Gap | Address in |
|---|---|
| Override layer (ADR-040/041) | Phase 1C |
| Decision slot graceful failure (ADR-086) | Phase 1A |
| Provider capabilities + bounce/complaint (ADR-101, ADR-106) | Phase 2C (alongside send prep) |
| Signal layer (ADR-110–113) | Phase 3C |
| Snapshot completeness (ADR-062) | Phase 2C (alongside send prep) |
| Merge context (ADR-005) | Phase 3 (per-recipient rendering is tied to segmentation) |
| Content versioning (ADR-128) | Phase 2A (alongside content management) |

---

### Suggested next steps (immediate)

1. **Phase 1A — decision strategy contract** — small, high-leverage, already have the registry structure. Good first session.
2. **Phase 1B — HTML template manifest format** — decision only, no code yet. One focused conversation.
3. **Phase 1C — override-event model** — design is settled (see Decision Log), just needs implementation.

After that, Phase 2 (editing frontends) unblocks the demo path and makes everything showable to clients.

---

## 7. Open Questions

- [x] Phase 1B: MJML as template format, frontmatter in file, compiled in frontend layer (ADR-131)
- [ ] Phase 3C: design the signal layer before building — what are the signal types, decay model, storage? Also needs to cover: category/content deletion vs. archival policy — archived categories stop contributing new preference scoring, existing influence decays via the same time-based decay mechanism rather than being force-zeroed (see `docs/backlog.md` § Needs ADR).
- [ ] Phase 4A: playbook structure and communication style decisions
- [ ] Which 2–3 real client cases map best to the three pillars?
