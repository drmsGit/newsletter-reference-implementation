---
type: adr
status: proposed
topic:
  - privacy
  - gdpr
  - architecture
  - recipients
  - governance
created: 2026-06-06
modified: 2026-06-06
---

## Status
Proposed

## Context

The platform stores and processes information related to:

- Recipients
- Preferences
- Campaign participation
- Engagement events
- Behavioral history
- AI-generated recommendations
- Audience insights

Regulatory frameworks such as GDPR require organizations to support:

- Data access requests
- Data portability
- Data correction
- Data deletion
- Consent withdrawal

Many marketing systems implement these capabilities as operational afterthoughts, resulting in complex, incomplete, and error-prone privacy processes.

## Decision

Privacy operations shall be considered a first-class architectural capability.

Every component storing recipient-related information must support:

- Data discovery
- Data export
- Data correction
- Data deletion

through a standardized privacy interface.

Privacy requests may originate from:

- Internal users
- CRM systems
- Customer service systems
- External APIs
- Self-service customer portals

The architecture shall not require manual database analysis or custom scripts to fulfill privacy requests.

### Privacy Layer

A dedicated Privacy Layer shall exist as a cross-cutting architectural concern.

Responsibilities include:

- Data discovery
- Data export
- Data correction
- Data deletion
- Consent synchronization
- Auditability of privacy operations

The Privacy Layer is independent from the Delivery Layer and applies across all platform domains.

### Recipient Identity Principle

Recipient-related processing should be based on a platform-specific RecipientId wherever possible.

Most platform components should not require direct knowledge of email addresses.

Example:

```text
RecipientId
→ Preferences
→ Engagement
→ Recommendations
→ Audience Insights
```

Email addresses should remain within CRM and delivery systems whenever possible.

### Data Deletion Requirements

Deletion of a recipient shall include all associated information, including:

- Preferences
- Behavioral history
- Campaign participation history
- Recommendation profiles
- AI-generated recipient profiles
- Stored personalization artifacts

Components shall expose deletion capabilities through a common privacy interface.

## Consequences

### Positive

- GDPR compliance by design
- Reduced technical debt
- Easier CRM integration
- Simplified future audits
- Consistent privacy handling across components

### Negative

- Additional implementation effort
- More complex data models
- Clear separation between personal and aggregated data required

## Notes

Privacy requirements are not optional operational processes. They are core platform capabilities.

Building privacy operations into the architecture from the beginning reduces future compliance risks, lowers operational costs, and simplifies system evolution.

Privacy is a platform capability, not an operational afterthought.

## Related ADRs

### Referenced By

- [[ADR-001 — Newsletter Architecture Boundaries]]
- [[ADR-002 — API First Architecture]]
