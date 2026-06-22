---
type: architecture-model
status: draft
topic:
  - architecture
  - implementation
created: 2026-06-05
modified: 2026-06-05
---

# Reference Architecture - Minimal Implementation Path

## Purpose

This model shows the smallest useful implementation of the reference architecture.

It is intended for small teams or organizations starting from scratch.

## Minimal Architecture

```mermaid
flowchart LR

CRM[CRM<br/>Recipient + Consent]
CONTENT[Content Catalog]
BUILDER[Newsletter Builder]
RENDER[Rendering Layer]
PROVIDER[Provider<br/>SendGrid / SES / Brevo]

CRM --> BUILDER
CONTENT --> BUILDER
BUILDER --> RENDER
RENDER --> PROVIDER
```

## Minimal Responsibilities

### CRM

- recipientId
- email
- consent status
- createdAt
- modifiedAt
- optional country and language

### Content Catalog

- reusable content records
- metadata
- categories
- image URLs

### Newsletter Builder

- campaign
- variant
- module instances
- overrides
- subject
- preheader

### Rendering Layer

- final HTML
- tracking metadata
- optional snapshot

### Provider

- send email
- return at least bounce and complaint feedback

## Optional Growth Path

```mermaid
flowchart LR

MIN[Minimal Architecture]
AUTO[Automation Layer]
DECISION[Decision Layer]
INSIGHT[Insight Layer]
DWH[DWH / Data Store]
AI[AI Assistance]

MIN --> AUTO
MIN --> DECISION
MIN --> INSIGHT
INSIGHT --> AI
DWH --> INSIGHT
AUTO --> DECISION
```

## Related ADRs

- [[ADR-125 — Define a Minimal Reference Architecture]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-121 — Minimal Recipient Model]]
- [[ADR-124 — DWH Is Recommended but Not Mandatory]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
