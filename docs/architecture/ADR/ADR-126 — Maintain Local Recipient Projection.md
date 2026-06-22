---
type: adr
status: accepted
topic:
  - architecture
  - foundation
created: 2026-06-16
modified: 2026-06-16
source:
  - interview-2026-06-16
depends_on:
enables:
---
## Status

Accepted

## Context

The architecture requires recipient-related information for:

- personalization
- decision strategies
- rendering
- delivery execution tracking
- engagement analysis

At the same time, the platform is not intended to replace an organization’s CRM, CDP or customer master data system.

The platform must remain capable of operating with different external customer systems while still supporting local decision making and communication workflows.

## Decision

The platform may maintain a local Recipient Projection.

A Recipient Projection contains only the recipient attributes required by the communication platform.

Examples include:

- recipient identifier
- language
- preferred airport
- communication preferences
- segmentation attributes
- decision-related attributes

The Recipient Projection is not considered the customer source of truth.

The external CRM, CDP or customer master data system remains the authoritative source of customer data.

## Recipient Identity

Each Recipient must contain:

```text
internal recipient identifier
external recipient identifier
```

The external identifier links the recipient to the originating source system.

Examples:

```text
CRM Contact ID
Customer ID
Loyalty ID
Member ID
```

The architecture must avoid using email addresses as primary identifiers.

Email addresses are considered mutable communication attributes.

## Allowed Responsibilities

The Recipient Projection may be used for:

- personalization
- communication decisions
- rendering
- delivery execution tracking
- engagement analysis
- communication history

## Forbidden Responsibilities

The Recipient Projection must not become:

- a CRM replacement
- a customer master database
- a full customer profile repository
- a system of record for customer data

Business ownership of customer information remains outside the communication platform.

## Synchronization

Recipient data may be:

- imported
- synchronized
- projected
- cached

from external systems.

Synchronization mechanisms are implementation-specific and outside the scope of this ADR.

The architecture only requires that recipient data can be associated with an external source identifier.
## Consequences

### Positive

- supports personalization
- supports decision strategies
- supports communication history
- keeps CRM ownership intact
- remains vendor-neutral
- simplifies delivery and engagement tracking

### Negative

- introduces data duplication
- requires synchronization with source systems
- requires clear ownership boundaries

## Rationale

Decision engines, rendering and engagement tracking require recipient-related information.

Requiring direct access to an external CRM for every communication decision would introduce tight coupling and reduce portability.

A lightweight Recipient Projection provides the necessary communication context while preserving the principle that customer ownership remains outside the communication platform.

The platform owns communication state.

The CRM owns customer state.

## Related ADRs

- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-121 — Minimal Recipient Model]]