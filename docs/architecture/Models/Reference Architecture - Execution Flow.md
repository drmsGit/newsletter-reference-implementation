---
type: architecture-model
status: draft
topic:
  - architecture
  - execution
created: 2026-06-05
modified: 2026-06-05
---

# Reference Architecture - Execution Flow

## Purpose

This model shows how a campaign moves from editable composition to actual delivery.

## Diagram

```mermaid
flowchart TD

CAMPAIGN[Campaign<br/>Newsletter-level context]
VARIANT[Variant<br/>Human-created composition]
MODULES[Module Instances<br/>Ordered structure]
SLOTS[Decision Slots<br/>Dynamic content placeholders]
DECISION[Decision Resolution<br/>Resolved content per context]
RENDER[Rendering Layer<br/>Final HTML generation]
SNAPSHOT[Snapshot<br/>Final send state]
SEND[Send Instance<br/>Concrete execution]
DELIVERY[Delivery Execution<br/>Recipient-level send records]
PROVIDER[Provider<br/>Send + feedback]
EVENTS[Engagement Events]

CAMPAIGN --> VARIANT
VARIANT --> MODULES
VARIANT --> SLOTS
SLOTS --> DECISION
MODULES --> RENDER
DECISION --> RENDER
RENDER --> SNAPSHOT
SNAPSHOT --> SEND
SEND --> DELIVERY
DELIVERY --> PROVIDER
PROVIDER --> EVENTS
```

## Key Rules

- Campaign equals newsletter-level context.
- Variant equals composition.
- Decision Slots resolve content, not structure.
- Snapshot belongs to Send Instance, not to Variant.
- Delivery Execution records what was sent to whom.
- Engagement Events record what happened afterwards.

## Related ADRs

- [[ADR-020 — Campaign Equals Newsletter]]
- [[ADR-021 — Variants Are Human Created Versions]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-053 — Maintain Minimal Delivery Execution History]]
