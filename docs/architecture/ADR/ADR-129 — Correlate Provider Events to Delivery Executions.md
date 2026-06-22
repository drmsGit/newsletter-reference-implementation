---
type: adr
status: accepted
topic:
  - delivery
  - provider
  - events
  - tracking
  - engagement
  - webhook
created: 2026-06-17
modified: 2026-06-17
---

## Status
Accepted

## Context

The architecture normalizes provider-specific delivery and engagement events into canonical Engagement Events.

Examples:

```text
send
delivered
open
click
bounce
complaint
unsubscribe
```

Providers use different identifiers and event formats.

Examples:

```text
Message ID
Event ID
Tracking ID
Recipient ID
Metadata
```

The platform must reliably associate incoming provider events with the correct Delivery Execution.

The correlation strategy must remain provider-independent.

The architecture must not depend on any single provider's event model.

## Decision

The architecture correlates provider events to Delivery Executions.

Delivery Execution is the authoritative delivery record.

Provider identifiers are considered external references.

Provider events must be mapped to a Delivery Execution before they enter the Insight Domain.

### Primary Correlation

```text
provider_message_id
```

When a provider returns a unique message identifier during send execution, the platform stores that identifier on the Delivery Execution.

Example:

```text
DeliveryExecution
id = 4711
provider_message_id = abc123
```

Incoming provider events referencing `abc123` must resolve to `DeliveryExecution 4711`.

This is the preferred correlation strategy.

### Secondary Correlation

```text
custom metadata
```

If supported by the provider, the platform may include internal identifiers in outbound metadata.

Examples:

```text
delivery_execution_id
send_instance_id
recipient_id
```

Provider events may then return that metadata.

This provides an additional correlation mechanism independent of provider message identifiers.

### Fallback Correlation

```text
recipient_id + send_instance_id
```

If neither `provider_message_id` nor metadata are available, correlation may use a combination of recipient and send context.

Example:

```text
recipient_id = 123
send_instance_id = 456
```

This strategy is less reliable and should only be used as a fallback.

### Provider Event Boundary

Provider-specific event payloads must not enter the core architecture directly.

Provider adapters are responsible for translating a Provider Event into a Canonical Engagement Event.

Example:

```text
Brevo Event → Provider Adapter → Engagement Event
Resend Event → Provider Adapter → Engagement Event
SES Event   → Provider Adapter → Engagement Event
```

The Insight Domain only processes canonical events.

### Canonical Engagement Event

Every canonical event must reference `delivery_execution_id` before it is persisted.

Example:

```text
EngagementEvent
├─ delivery_execution_id
├─ event_type
├─ provider
├─ provider_event_id
└─ event_data
```

This guarantees a consistent downstream model.

### Handling Unmatched Events

A provider event may arrive without a valid correlation.

Examples:

- missing provider_message_id
- deleted delivery execution
- malformed metadata
- provider inconsistency

In these situations the event must not be silently discarded.

The platform should store, log, quarantine, or retry depending on implementation requirements.

The architecture requires that unmatched events remain traceable.

## Consequences

### Positive

- keeps provider implementations isolated
- supports provider replacement
- creates a stable engagement model
- simplifies reporting
- simplifies preference updates
- simplifies future AI features
- supports multiple providers simultaneously

### Negative

- requires correlation logic in provider adapters
- requires provider identifier storage
- requires handling unmatched provider events

## Notes

The platform owns communication history.

Delivery Execution is the canonical recipient-level delivery record.

Provider identifiers are temporary integration details.

By correlating provider events to Delivery Executions at the integration boundary, the core architecture remains provider-neutral while preserving a complete delivery and engagement history.

The principle is:

```text
Provider events are external facts.
Delivery Executions are internal truth.
```

## Related ADRs

### Referenced By

- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-127 — Decision Execution May Use Recipient Context]]
