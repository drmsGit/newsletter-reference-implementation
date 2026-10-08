---
type: moc
topic:
  - architecture
  - ai-architecture
created: 2026-08-02
modified: 2026-08-02
---

# MOC - AI Architecture

The AI capability layer: what AI is allowed to do, in which of three modes (Assistive, Autonomous, Development — lettered A, B and C in the ADRs; the key is ADR-140's 2026-10-08 addendum), and under what data, model and cost governance. Designed as five ADRs in the 2026-07-31 AI-layer interview; Assistive is built.

## ADRs

- [[ADR-140 — AI Capability Layer]]
- [[ADR-141 — In-App Assistive AI Actions]] — Assistive: in-app actions a person asks for
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]] — Autonomous: orchestrated workflows
- [[ADR-143 — AI-Assisted Development Boundary]] — Development: AI-assisted development
- [[ADR-144 — AI Data and Model Governance]] — model adapter, PII line, spend cap

## Note — "AI" means two different things in this architecture

The ADRs above describe a **language-model capability layer**. The decision-layer ADRs — [[ADR-080 — Human-governed Taxonomy Before AI Selection]], [[ADR-081 — AI Ranks Within Governed Candidate Sets]], [[ADR-082 — AI May Recommend but Not Publish]] — are written **model-agnostically**, and live in [[MOC - Decision Architecture]].

ADR-081's *"AI ranks within governed candidate sets"* is fully satisfied by a learned ranking model and **does not imply a language model**. Nothing currently states which kind of AI belongs where, and that ambiguity is what allowed an LLM to be costed into the per-recipient decision path before the arithmetic was checked. The open question — and the finding that per-recipient LLM *selection* is the wrong tool rather than merely an expensive one — is recorded in `docs/backlog.md` § Needs ADR.

## Related MOCs

- [[MOC - Tarrow]]
- [[MOC - Decision Architecture]]
- [[MOC - Automation Architecture]]
- [[MOC - Security Architecture]]
