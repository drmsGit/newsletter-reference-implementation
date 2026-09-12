---
type: adr
status: accepted
topic:
  - architecture
  - crm
  - data-model
created: 2026-06-01
modified: 2026-09-12
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

## Addendum 2026-09-12 — `email` and `consent status` move out of the minimum fields

Prompted by [[ADR-163 — Per-Channel Consent and Addressability]], which broke
the one-address, one-consent-state assumption this ADR's minimum field list
was written against.

The Decision above lists `email` and `consent status` among the minimum
recipient fields. Both move out of the recipient model itself, under
ADR-163, for reasons specific to each field:

- **`email`** becomes one row among possibly many in a new addressability
  table, because a recipient can have many contact points across channels —
  push tokens (one per device), a postal address, a phone number — and
  cardinality, lifecycle (tokens expire) and structure (a postal address is
  not a string) all forced that table off `RecipientDB`.
- **`consent status`** is replaced by append-only consent events keyed
  `(recipient, channel, purpose)`, because a single mutable column cannot
  express per-channel, per-purpose consent, and cannot carry the source and
  timestamp that make a grant provable.

**This is a wording/scope addendum, not a superseding decision, and the
model stays minimal in spirit.** The recipient record itself is still small
— `recipientId`, `createdAt`, `modifiedAt` and the recommended/optional
fields are untouched. What changes is only that the two fields this ADR
named *concretely* no longer live on the recipient record: they live in the
addressability table and the consent-event log respectively, each governed
by ADR-163. The minimalism principle this ADR argues for is exactly what
motivated moving them out rather than growing `RecipientDB` a column per
channel.

## Related ADRs

### Depends On

- [[ADR-120 — CRM as Customer Source of Truth]]

### Enables

- [[ADR-054 — Use Internal Recipient Identifiers]]

### Referenced By

- [[ADR-163 — Per-Channel Consent and Addressability]]
