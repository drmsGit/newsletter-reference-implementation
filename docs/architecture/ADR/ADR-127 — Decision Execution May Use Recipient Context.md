---
type: adr
status: accepted
topic:
  - decision
  - personalization
  - recipients
  - recipient-context
  - architecture
created: 2026-06-16
modified: 2026-06-16
---

## Status
Accepted

## Context

The architecture separates:

- Campaign
- Variant
- Module Instance
- Decision Slot
- Decision Resolution
- Snapshot
- Delivery Execution

Decision Slots define where a decision is required inside a Variant.

A Decision Resolution records what was actually selected.

Initially, Decision Resolutions may be global for a Variant or Decision Slot.

However, personalized communication requires that different Recipients may receive different content for the same Decision Slot.

Example:

```text
Same Campaign
Same Variant
Same Decision Slot

Recipient A → Beach Content
Recipient B → City Content
Recipient C → Nature Content
```

This requires Decision Execution to optionally use Recipient-specific context.

## Decision

Decision Execution may use Recipient Context.

A Decision Strategy may evaluate:

- Decision Slot configuration
- Candidate filters
- Content metadata
- Category assignments
- Recipient preferences
- Recipient attributes
- Engagement history
- other decision-relevant recipient context

The Decision Slot still defines the decision intent.

The Decision Strategy defines how the decision is made.

The Decision Resolution records the result.

### Decision Slot

A Decision Slot describes what should be decided.

Example:

```text
Recommend one travel inspiration item
from Beach or City categories
```

The Decision Slot does not store the selected content.

### Recipient Context

Recipient Context may include:

- Recipient Projection attributes
- Recipient Preferences
- language
- country
- engagement history
- previous decisions
- service data
- purchase data
- consent-safe behavioral signals

Recipient Context must be limited to data allowed by consent, governance and privacy rules.

### Decision Resolution

A Decision Resolution records the result of a decision execution.

For recipient-aware decisions, the Decision Resolution must be attributable to the recipient context used during execution.

The architecture must support both:

```text
Global Decision Resolution
```

and

```text
Recipient-specific Decision Resolution
```

depending on the decision type and strategy.

### Execution Modes

#### Global Execution

A Decision Slot may be executed once.

The resulting Decision Resolution is reused for all recipients.

Example:

```text
Select highest-scoring Beach content for this newsletter.
```

#### Recipient-Aware Execution

A Decision Slot may be executed separately per recipient or recipient group.

Example:

```text
Recipient A has high Beach preference.
Recipient B has high City preference.
```

The same Decision Slot may therefore resolve to different Content Records.

## Consequences

### Positive

- enables personalized communication
- supports recipient-specific recommendations
- supports preference-based decisions
- keeps Variant structure stable
- keeps personalization outside manual composition
- supports future AI-based decisioning

### Negative

- increases execution complexity
- may create many Decision Resolutions
- requires careful auditability
- requires clear privacy and consent boundaries
- requires provider delivery to support recipient-specific outcomes

## Notes

The architecture should not require a separate Variant for every recipient-specific content choice.

The Variant defines the communication structure.

Decision Slots define where dynamic selection is allowed.

Decision Strategies resolve those slots using the available context.

This allows Marketing to guide the communication while the system optimizes content selection.

The principle is:

```text
Human-guided marketing.
System-optimized decision execution.
```

## Related ADRs

### Referenced By

- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-121 — Minimal Recipient Model]]
- [[ADR-126 — Maintain Local Recipient Projection]]
