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

---

## 6. Roadmap

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

**1B. Plugin contract: HTML email templates**
Decide on a manifest format: each email module template (e.g. `2col_product.html`) has a sidecar or frontmatter block declaring its variables (`{{ headline }}`, `{{ image_url }}`, etc.) and a human-readable label. Drop a file into the right folder, it appears in the campaign builder. Decision needed: frontmatter in the HTML itself (like Jekyll) or a companion `.json` file?

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

- [ ] Phase 1B: frontmatter-in-HTML vs. companion `.json` for template variable declarations?
- [ ] Phase 3C: design the signal layer before building — what are the signal types, decay model, storage?
- [ ] Phase 4A: playbook structure and communication style decisions
- [ ] Which 2–3 real client cases map best to the three pillars?
