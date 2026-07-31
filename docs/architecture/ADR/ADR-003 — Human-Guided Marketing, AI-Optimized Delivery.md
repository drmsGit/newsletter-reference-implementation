---
type: adr
status: accepted
topic:
  - ai
  - marketing
  - automation
  - governance
created: 2026-06-06
modified: 2026-07-31
source:
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31)"
enables:
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-141 — In-App Assistive AI Actions]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
---

## Status
Accepted

## Context

Marketing teams spend a significant portion of their time on repetitive operational activities such as:

- Selecting content
- Building newsletter variants
- Ordering modules
- Optimizing send times
- Managing audience splits
- Executing product-focused campaigns

These activities are often driven by commercial goals and performance targets rather than customer understanding.

At the same time, marketers create the greatest value when they:

- Discover customer interests
- Develop content strategies
- Create narratives and campaigns
- Identify emerging trends
- Build customer relationships
- Define business and communication goals

As AI capabilities improve, there is a risk of focusing automation on replacing marketers instead of reducing operational workload.

## Decision

The architecture shall prioritize automation of delivery and optimization tasks while preserving human ownership of strategy, creativity, and customer understanding.

The system should:

- Automate repetitive campaign execution activities
- Optimize content selection and ordering
- Optimize frequency and send timing
- Generate recommendations and suggestions
- Surface customer insights

The system should not assume fully autonomous marketing decision-making.

Human marketers remain responsible for:

- Strategic direction
- Campaign objectives
- Brand voice
- Customer research
- Content creation
- Approval and governance

### Preferred AI Features

- Content recommendations
- Newsletter scoring
- Audience insights
- Dynamic content selection
- Frequency optimization
- Send-time optimization
- Variant suggestions

### Secondary AI Features

- Subject line generation
- Copy suggestions

### Not a Primary Goal

- Fully autonomous marketing strategy
- Fully autonomous campaign planning
- Removal of human campaign ownership

### How this philosophy is realized (2026-07-31 AI-layer interview)

The intent above is made concrete by the AI-layer ADRs. Key refinements settled in
the design interview:

- **Trust = "reversible + audited + a human can interfere," not "everything is a
  pending proposal."** "AI proposes, human governs" is realized as **direct write
  by default** — actions are reversible via the Override Layer (ADR-040/041), fully
  audited, and interruptible. **Approval is a per-task setting** (auto-apply vs
  require-approval), not a global gate, giving **graduated trust**: a task can move
  from approval-first to auto once a company trusts it. AI plugs in behind the
  existing seams (provider-adapter + plugin-registry), stays **optional per
  capability**, and always has a global kill switch. See
  [[ADR-140 — AI Capability Layer]].
- **AI works in three modes:** **A** — in-app assistive actions a marketer triggers
  ([[ADR-141 — In-App Assistive AI Actions]]); **B** — autonomous workflows / the
  automation boundary (mostly n8n, planned ADR-142); **C** — AI-assisted
  *development*, never production (planned ADR-143).
- **Governance is cross-cutting** ([[ADR-144 — AI Data and Model Governance]]): a
  swappable model adapter (with an EU worked example), a "no raw PII by default"
  line (personalise via merge variables, ADR-005), a per-role spend cap, a
  company-editable "DON'T EVER" guardrail, and manager-owned, versioned prompts.
- **Preferred vs Secondary above is a *value* ranking, not a build order.**
  Subject-line generation is listed "Secondary" by value, yet it is the **first**
  Mode-A action built (it is the easiest, lowest-risk starting point) — see
  ADR-141. The two orderings are deliberately separate.

## Consequences

### Positive

- Increased marketing productivity
- More time for strategic work
- Better customer understanding
- Improved scalability
- Reduced operational effort
- Easier adoption by marketing teams

### Negative

- Lower level of full automation
- Continued need for human review and governance
- Some optimization opportunities may remain intentionally constrained

## Notes

The objective of AI is not to replace marketing teams.

The objective is to free marketing teams from repetitive optimization work so they can spend more time understanding customers and developing better communication strategies.

Commercial product promotion is often highly rule-based and performance-driven, making it a suitable candidate for automation.

Customer understanding, storytelling, creativity, and strategic planning remain primarily human responsibilities.

The system maximizes relevance and efficiency. Marketers maximize insight and creativity.

## Related ADRs

### Enables

- [[ADR-140 — AI Capability Layer]]
- [[ADR-141 — In-App Assistive AI Actions]]
- [[ADR-144 — AI Data and Model Governance]]

### Referenced By

- [[ADR-001 — Newsletter Architecture Boundaries]]
