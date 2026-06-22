---
type: adr
status: accepted
topic:
  - architecture
  - snapshot
  - delivery
  - personalization
  - auditability
  - ownership
created: 2026-06-08
modified: 2026-06-08
---

## Status
Accepted

## Context

The architecture must support both static and highly personalized communication.

A fundamental requirement is the ability to answer:

> What did this recipient receive at send time?

At the same time, storing one complete HTML file permanently for every recipient and every send can become operationally expensive and unnecessary.

The architecture must also support different delivery providers with different capabilities:

- providers that accept rendered HTML
- providers that support templates and merge variables
- providers that support personalization payloads
- providers that support recipient-specific content

The system must remain provider-independent.

## Decision

The architecture separates four distinct concepts:

1. Snapshot State
2. Decision Resolution
3. Merge Context
4. Delivery Artifact

These concepts serve different purposes and must not be combined.

### Snapshot State

A Snapshot represents the frozen send-time state of a communication variant.

A Snapshot is owned by the platform and serves as the historical source of truth.

A Snapshot may be stored as a file, object storage artifact, database record, or future storage implementation. The storage mechanism is an implementation detail.

The purpose of a Snapshot is:

- auditability
- reconstruction
- debugging
- compliance
- historical analysis

A Snapshot is not defined by how a provider receives content.

### Decision Resolution

A Decision Resolution records which dynamic content was selected at send time.

Example:

```text
Decision Slot: Beach Recommendation
Selected Content: Mallorca Beach Walk
Reason: Highest score in Beach category
```

Decision Resolutions must remain available after delivery.

### Merge Context

Merge Context contains recipient-specific personalization values used at send time.

Example:

```text
firstname = Diede
language = de
preferred_airport = BER
```

Merge Context must remain available after delivery.

### Delivery Artifact

A Delivery Artifact represents the provider-facing payload.

Delivery Artifacts are generated from:

```text
Snapshot + Decision Resolution + Merge Context
```

The Delivery Layer may create:

- one shared HTML artifact
- one variant-specific HTML artifact
- one recipient-specific HTML artifact
- provider templates
- provider-specific payload structures

The Delivery Layer decides which artifact is required for a given provider.

### Provider Payload Independence

Internal storage and provider delivery are independent concerns.

The platform owns communication state. Providers consume delivery artifacts.

The architecture explicitly allows provider payloads to contain full rendered HTML:

```json
{
  "to": "recipient@example.com",
  "subject": "Summer Newsletter",
  "html": "<!doctype html>..."
}
```

The architecture does not assume a 4 KB limitation or similar field-size restrictions for provider delivery payloads.

Modern delivery providers typically support payload sizes significantly larger than typical CRM field limitations.

Provider capabilities must not influence the internal storage model.

### Send Rules

#### Static Send

If no personalization and no dynamic content is used:

```text
One Snapshot → Many Delivery Executions
```

No recipient-specific HTML storage is required.

#### Merge Personalization

If only merge fields are used:

```text
Snapshot + Merge Context + Delivery Execution
```

Recipient-specific HTML does not need to be stored permanently if reconstruction remains possible.

#### Dynamic Content

If content differs between recipients:

```text
Snapshot + Decision Resolution + Merge Context + Delivery Execution
```

Recipient-specific HTML may be generated when required.

#### Recipient-Specific Delivery Artifacts

The Delivery Layer may generate recipient-specific HTML artifacts:

```text
Snapshot + Resolution + Merge Context
↓
Rendered Recipient HTML
↓
Provider Delivery
```

Recipient-specific delivery artifacts are considered temporary operational artifacts. They may be deleted after successful provider handoff. Permanent storage is not required if the original send-time state remains reconstructable.

#### Provider Handoff

Provider adapters may transform stored snapshots into provider-specific payloads:

```text
Snapshot File → Provider Adapter → API Payload
```

or

```text
Snapshot → Template Mapping → Provider Template Send
```

or

```text
Snapshot + Resolution + Merge Context → Recipient HTML → Provider API
```

All approaches are valid.

## Consequences

### Positive

- provider independence
- storage efficiency
- supports dynamic content
- supports personalization
- preserves auditability
- allows reconstruction of recipient experiences
- supports future delivery providers
- avoids permanent storage of unnecessary recipient HTML artifacts

### Negative

- reconstruction may require multiple objects
- delivery layer becomes more sophisticated
- highly personalized sends may generate large numbers of temporary artifacts

## Notes

Auditability and delivery are related but separate concerns.

The platform must know what was sent. The platform does not need to permanently store every generated recipient-specific HTML artifact.

Instead, the platform stores the state required to reconstruct what was sent:

```text
Snapshot + Decision Resolution + Merge Context
```

Delivery providers receive artifacts generated from this state.

The platform owns communication state. Providers consume delivery artifacts.

This separation preserves ownership, portability and provider independence while keeping storage requirements manageable.

## Related ADRs

### Enables

- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-062 — Snapshot Stores Final Render State]]
- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
- [[ADR-128 — Version Content for Auditability and Restoration]]
- [[ADR-129 — Correlate Provider Events to Delivery Executions]]
