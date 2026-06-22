---
type: moc
topic:
  - architecture
created: 2026-05-30
modified: 2026-06-05
---

# MOC - Newsletter Architecture

	# MOC - Newsletter Architecture

## Architecture Principles

- [[Newsletter Architecture Design Principles]]

## Foundation

- [[ADR-001 — Newsletter Architecture Boundaries]]
- [[ADR-002 — API First Architecture]]
- [[ADR-003 — Human-Guided Marketing, AI-Optimized Delivery]]
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-125 — Define a Minimal Reference Architecture]]

## Architecture Areas

- [[MOC - Content Architecture]]
- [[MOC - Composition Architecture]]
- [[MOC - Rendering Architecture]]
- [[MOC - Delivery Architecture]]
- [[MOC - Decision Architecture]]
- [[MOC - Automation Architecture]]
- [[MOC - Provider Architecture]]
- [[MOC - Insight Architecture]]
- [[MOC - Data Foundation]]

## Main Architecture Flow

```mermaid
graph LR
  CRM[CRM / Recipient Source] --> CONTENT[Content Source of Truth]
  CONTENT --> COMP[Campaign / Composition]
  COMP --> DECISION[Decision Slots / Decision Layer]
  DECISION --> RENDER[Rendering Layer]
  RENDER --> DELIVERY[Delivery Layer]
  DELIVERY --> PROVIDER[Provider]
  PROVIDER --> EVENTS[Engagement Events]
  EVENTS --> INSIGHT[Insight Layer]
  INSIGHT --> DECISION
```

## Minimal Reference Architecture

```mermaid
graph LR
  CRM[CRM] --> CONTENT[Content Catalog]
  CONTENT --> BUILDER[Newsletter Builder]
  BUILDER --> RENDER[Rendering Layer]
  RENDER --> PROVIDER[Provider]
```

## Extended Architecture

```mermaid
graph LR
  CRM[CRM] --> AUD[Audience / Segments]
  AUD --> AUTO[Automation Layer]
  AUTO --> CAMP[Campaign]
  CAMP --> DEC[Decision Layer]
  DEC --> REND[Rendering]
  REND --> DEL[Delivery]
  DEL --> PROV[Provider]
  PROV --> EV[Engagement Events]
  EV --> INS[Insight Layer]
  INS --> DEC
  DWH[DWH / Data Store] --> INS
  DWH --> DEC
```

## Principles

- [[Newsletter Architecture Design Principles]]
