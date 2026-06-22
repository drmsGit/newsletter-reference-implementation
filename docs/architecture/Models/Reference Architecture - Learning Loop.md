---
type: architecture-model
status: draft
topic:
  - architecture
  - insight
  - decision
  - automation
created: 2026-06-05
modified: 2026-06-05
---

# Reference Architecture - Learning Loop

## Purpose

This model shows how the architecture learns from delivery and engagement without depending on a single provider.

## Diagram

```mermaid
flowchart TD

PROVIDER[Provider Feedback<br/>opens, clicks, bounces, complaints]
EVENTS[Engagement Events<br/>normalized internal model]
INSIGHT[Insight Layer<br/>signals]
RS[Recipient Signals]
CS[Content Signals]
COS[Composition Signals]
SS[Segment Suggestions]
DECISION[Decision Layer<br/>ranking + personalization]
AUTOMATION[Automation Layer<br/>orchestration + timing]
CONTENT[Content Catalog<br/>governed content]
CAMPAIGN[Campaign / Variant<br/>composition]

PROVIDER --> EVENTS
EVENTS --> INSIGHT

INSIGHT --> RS
INSIGHT --> CS
INSIGHT --> COS
INSIGHT --> SS

RS --> DECISION
CS --> DECISION
COS --> DECISION
SS --> AUTOMATION

CONTENT --> DECISION
DECISION --> CAMPAIGN
AUTOMATION --> CAMPAIGN
```

## Key Rules

- Engagement Events are normalized before use.
- Insight Layer answers: what happened?
- Decision Layer answers: what should be selected next?
- Automation Layer answers: when and why should communication happen?
- AI may recommend, but not publish unapproved content.

## Related ADRs

- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-056 — Engagement Events as Foundation for Automation]]
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]
- [[ADR-082 — AI May Recommend but Not Publish]]
- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
- [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]
- [[ADR-112 — Signals Use Time-Based Decay]]
- [[ADR-113 — Separate Operational and Historical Signals]]
