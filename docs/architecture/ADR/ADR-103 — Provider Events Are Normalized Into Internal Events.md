---
type: adr
status: accepted
topic:
  - architecture
  - provider
  - analytics
created: 2026-06-01
modified: 2026-09-12
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-102 — Rendering Prepares Tracking Metadata]]"
enables:
  - "[[ADR-055 — Separate Delivery Execution from Engagement Events]]"
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
---


## Status

Accepted

## Context

Providers expose different event models.

Direct usage would create provider lock-in.

## Decision

Provider-specific events must be transformed into a provider-independent internal event model.

Examples:

- open
- click
- bounce
- complaint
- unsubscribe

## Consequences

### Positive

- provider independence
- reusable analytics
- reusable automation logic

### Negative

- event transformation layer required

## Addendum 2026-09-12 — scope clarification: per-recipient events only

Prompted by [[ADR-164 — Channel Feedback and Signals]] point 5, which needed
this ADR to state its scope explicitly once omni-channel introduced feedback
that has no recipient at all — an ad platform reporting "340 of 500 matched"
for an audience-and-creative, not for a person.

This is a **scope clarification, not a Decision change.** This ADR governs
**per-recipient events only**. An internal event, in this ADR's sense, carries
a recipient by construction: it feeds the signal layer and attributes to
content precisely because it is something *a specific person* did — opened,
clicked, bounced, complained, unsubscribed.

Something reported per audience-and-creative over a period — an aggregate
sync result from a delegated channel such as paid social — is not a smaller
or degraded version of that. It is a **different grain entirely: a metric,
not an event in this ADR's sense.** A metric has its own table, keyed by what
it is actually about (audience or send instance, creative or variant, metric
name, value, period), and its own consumer — analytics, a human-read view —
never this one. Calling both "events" is what makes a null `recipient_id`
look like the natural way to fit aggregate data into this ADR's model; it
is not, and this addendum states why explicitly.

**The rule, stated so it cannot be worked around silently: an event without a
recipient is refused at ingestion, not stored with a null `recipient_id`.**
That refusal is what keeps aggregate, audience-level data from silently
corrupting the per-recipient signal layer this ADR feeds — the per-recipient
guarantee holds only if nothing without a recipient is ever accepted as one
of these events in the first place.

## Related ADRs

### Depends On

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-102 — Rendering Prepares Tracking Metadata]]

### Enables

- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-110 — Insight Layer Transforms Events Into Signals]]

### Referenced By

- [[ADR-164 — Channel Feedback and Signals]]
