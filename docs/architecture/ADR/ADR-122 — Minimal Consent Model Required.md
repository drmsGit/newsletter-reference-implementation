---
type: adr
status: accepted
topic:
  - architecture
  - crm
  - consent
created: 2026-06-01
modified: 2026-09-12
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
enables:
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
---


## Status

Accepted

## Context

Consent management is not a core responsibility of the newsletter architecture.

However, delivery decisions depend on consent information.

Transactional and marketing communication may require different consent handling.

## Decision

The architecture requires a minimal consent model.

At minimum, the system must distinguish between:

- marketing communication
- transactional communication

Only recipients eligible for the selected communication type may enter delivery processes.

## Consequences

### Positive

- safer communication handling
- compatible with different consent solutions
- supports transactional messaging

### Negative

- consent mapping required during integrations

## Addendum 2026-09-12 — widened to a `(channel, purpose)` grid

Prompted by [[ADR-163 — Per-Channel Consent and Addressability]], which
needed more than a single marketing/transactional distinction once consent
had to be tracked per channel as well as per communication type.

The Decision above distinguishes only marketing from transactional
communication. ADR-163 extends this to a **`(channel, purpose)` grid** —
consent is now tracked per channel and per purpose independently, e.g.
`(email, marketing)`, `(push, marketing)`, `(email, transactional)`. A real
case that motivates treating this as a genuine grid rather than a channel
label on the old two values: **`(paid_social, transfer)`** — a company
uploading a suppression list to an ad platform to *exclude* those people from
acquisition ads has no marketing intent toward them at all, so the transfer
itself needs its own consent purpose, independent of `(paid_social,
marketing)`, or that case cannot be expressed without claiming a consent
nobody gave.

This composes with the consent purpose-split already recorded as a proposed
amendment in [[ADR-150 — Tenancy and Access Model]]'s notes — marketing
opt-in versus transactional basis as distinct permissions on the same
person, with brand carried on the grant. That amendment and this one are the
same direction of travel, arrived at independently; ADR-163's `(channel,
purpose)` grid is the concrete shape the purpose axis takes.

**The minimal-consent principle is retained, not replaced.** Marketing versus
transactional remains the base distinction this ADR establishes as the
required minimum; the addendum widens the grid that distinction is tracked
on — adding channel as a second axis, and adding purposes such as `transfer`
where a channel's own mechanics demand it — it does not replace the
principle that a minimal, explicit consent distinction is required before a
recipient may enter delivery.

## Related ADRs

### Depends On

- [[ADR-120 — CRM as Customer Source of Truth]]

### Enables

- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]

### Referenced By

- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
