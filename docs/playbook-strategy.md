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

## 6. Open Questions / Next Steps

- [ ] Design the override/guideline layer to balance "psychological need for control" against "governed AI" pillar — in progress, see Decision Log 2026-06-24
- [ ] Define the decision-strategy plugin contract (inputs, outputs, required graceful-failure behavior per ADR-086, explainability reporting per ADR-085)
- [ ] Decide which 2-3 real client cases best illustrate each of the three pillars
- [ ] Design template/HTML module manifest format (how a dropped-in `.html` file declares its variables to the frontend)
- [ ] Eventually revisit drift report items not yet addressed: Merge Context (ADR-005), Snapshot completeness (ADR-062), Signal layer (ADR-110–113)
