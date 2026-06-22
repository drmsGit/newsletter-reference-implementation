---
type: adr
status: accepted
topic:
  - architecture
  - campaign
  - composition
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
enables:
  - "[[ADR-021 — Variants Are Human Created Versions]]"
  - "[[ADR-022 — Delivery Type Is Independent From Composition]]"
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
  - "[[ADR-095 — Use Send Instances for Technical Execution Tracking]]"
---


## Status
Accepted

## Context
The project needs a clear distinction between campaign, newsletter, variant, delivery and snapshot.
In the reference model, the operational unit called campaign is effectively one concrete newsletter/email concept.

## Decision
In the core architecture, a Campaign represents one newsletter/email-level context.
Campaign and Newsletter are treated as the same core concept.
Broader initiatives such as reactivation programs, Black Friday or multi-step journeys are represented through metadata or grouping, not as mandatory parent objects in the core model.

## Consequences

### Positive
- simplifies the core model
- makes CampaignId + VariantId the primary editable unit
- avoids mixing strategic marketing initiatives with concrete email compositions
- keeps grouping flexible for reporting and analytics

### Negative
- organizations may use the term campaign differently
- broader marketing initiatives need metadata or external grouping
- documentation must clearly define the term

## Notes
A reactivation journey with four emails should be modeled as four campaigns, optionally grouped by metadata. Each campaign may have its own variants.

## Related ADRs

### Enables

- [[ADR-021 — Variants Are Human Created Versions]]
- [[ADR-022 — Delivery Type Is Independent From Composition]]
- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]
- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
