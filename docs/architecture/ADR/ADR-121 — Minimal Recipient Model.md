---
type: adr
status: accepted
topic:
  - architecture
  - crm
  - data-model
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
enables:
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
---


## Status

Accepted

## Context

The reference architecture should define the minimum data required to operate a newsletter system.

## Decision

Minimum recipient fields:

- recipientId
- email
- consent status
- createdAt
- modifiedAt

Recommended fields:

- country
- language

Optional business-specific fields:

- lastPurchaseAt
- lastServiceContactAt
- customerStatus
- lifecycleStage

## Consequences

### Positive

- easier adoption
- clear minimum requirements
- supports personalization growth

### Negative

- business-specific extensions remain necessary

## Related ADRs

### Depends On

- [[ADR-120 — CRM as Customer Source of Truth]]

### Enables

- [[ADR-054 — Use Internal Recipient Identifiers]]
