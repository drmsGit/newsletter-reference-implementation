---
type: adr
status: proposed
topic:
  - architecture
  - channels
  - recipients
  - identity
  - boundaries
created: 2026-09-17
modified: 2026-09-17
source:
  - "User decision, 2026-09-17 (raised immediately after push became sendable); recorded in `docs/backlog.md`, Needs ADR"
depends_on:
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-126 — Maintain Local Recipient Projection]]"
  - "[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]"
  - "[[ADR-154 — Erasure and Retention]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]]"
enables:
---

## Status
Proposed

## Context

Push became sendable, and with it came the question the email channel never
had to ask: **the largest push audience is people who are not logged in, so
who are they in this platform?** An app install can hold a valid push token
long before the person behind it has signed in, or without them ever signing
in at all. Email has no equivalent — an address arrives from the CRM attached
to a known contact, so the platform has never had to say what it does with a
reachable someone nobody has identified.

[[ADR-126 — Maintain Local Recipient Projection]] already constrains the
answer more tightly than it first appears. It requires every recipient to
carry an external identifier linking it to the originating source system, and
it forbids the projection from becoming "a system of record for customer
data". The code enforces this rather than merely documenting it:
`recipients.external_id` is NOT NULL and UNIQUE, and the only production
creation path is an upsert keyed on it (`app/recipients/service.py:169`). A
recipient with no external owner cannot be created today, and that is not an
oversight to route around.

[[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] point 2
keeps identity resolution systems outside the core, unchanged from the
boundary [[ADR-001 — Newsletter Architecture Boundaries]] originally drew.
Reconnecting a device to a known person when they sign in **is** identity
resolution. It was therefore never the platform's work to do, and the question
"how do we merge the anonymous device into the real contact" was the wrong
question rather than an unanswered one.

**Two shapes were considered and rejected**, and the reasons are worth keeping
because each is sharper than the objection that first suggests itself.

The first is **one shared "push anonymous" contact** — the Selligent shape —
with every anonymous token hanging off a single system contact, re-pointed to
the real contact on login. The obvious objection is that it loses signal. The
real objection is worse: `SignalContributionDB` aggregates per recipient and
the decision engine reads that row, so every anonymous engagement would pile
onto one profile. It would not merely lose signal, it would feed the engine a
**corrupted affinity profile that grows with traffic** — the more the app is
used, the more confidently wrong that row becomes. Adopting the shape would
require an explicit rule excluding that contact from the signal layer, which
is a special case bolted onto
[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
to protect the platform from a record it chose to create.

The second is **one local recipient per device token**. It was rejected
because it makes the platform the system of record for a class of people
[[ADR-126 — Maintain Local Recipient Projection]] forbids it to own, and it
drags in the machinery that ownership implies: erasure per device — under
[[ADR-154 — Erasure and Retention]] an erasure takes everything connected to
the person, addressability rows included — and record merging when the device
turns out to belong to a known contact after all.
[[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] says neither
of those is ours.

## Decision

**1. The platform does not admit a recipient the CRM does not own.**
There is no anonymous recipient, no device-only local record, and no shared
placeholder contact. Every recipient reaching the platform carries an
`external_id` identifying it in the source system, exactly as
[[ADR-126 — Maintain Local Recipient Projection]] requires and the schema
already enforces.

**2. An app install that wants push becomes a contact in the source system
first.**
A device contact, an anonymous profile, whatever that system calls it — the
minting happens there. It then reaches the platform through the **ordinary
recipient sync**, carrying an `external_id` and a push address. There is no
second intake path and no push-specific one.

**3. The device is therefore never anonymous to the platform.**
What arrives is a recipient whose only address happens to be on the push
channel. Nothing about it is a new kind of entity: under
[[ADR-163 — Per-Channel Consent and Addressability]] point 2, addressability
is already one table holding every contact point whatever its type, so a
recipient with a push token and no inbox is a shape the model allows rather
than an exception to it.

**4. Reconnecting a device to a known contact on sign-in is the source
system's work.**
The platform receives the updated record through the same sync. It performs no
matching, no merging and no identity resolution, in line with
[[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] point 2.

**5. [[ADR-120 — CRM as Customer Source of Truth]] is untouched by this.**
This record does not widen or narrow what the CRM owns; it states that push
does not create an exception to it.

## Consequences

### Positive

- [[ADR-120 — CRM as Customer Source of Truth]],
  [[ADR-126 — Maintain Local Recipient Projection]],
  [[ADR-154 — Erasure and Retention]] and
  [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] all stay
  intact. No amendment, addendum or supersession is needed anywhere — the
  decision is the one those four records already implied.
- Token lifecycle needs nothing new.
  [[ADR-163 — Per-Channel Consent and Addressability]] point 2's "a status you
  can mark invalid beats a value you overwrite" already covers both renewal
  and abandonment, so there is no separate push-token expiry mechanism to
  design.
- Multi-device is already the model. Point 2 allows many addressability rows
  per `(recipient, channel)`, and point 11's fan-out rule sends to every valid
  token rather than picking one, so a person with a phone and a tablet needs
  no special handling.
- The signal layer is protected by construction rather than by an exclusion
  rule: engagement lands on the contact the source system minted, so no
  recipient row accumulates the behaviour of an undifferentiated crowd.

### Negative

- **A company with no CDP or CRM capable of minting a device contact cannot do
  anonymous push without building that step somewhere.** This is a real
  dependency, not a detail — it makes an external capability a precondition of
  a channel the platform otherwise supports end to end, and it belongs in the
  playbook stated plainly rather than discovered by an adopter mid-integration.
- **The recipient sync path is email-shaped and cannot accept a device
  contact.** `create_recipient` (`app/recipients/service.py:169`) takes
  `email` as a required positional; it calls `record_consent` with no channel,
  so a synced contact is granted **EMAIL** consent whatever it actually agreed
  to; and it writes only an email address row, via `_upsert_email_address`.
  A device contact — external id, a push token, no inbox — cannot be created
  through the only production path. Closing this means the sync path taking a
  **channel** and an address of that channel's shape. The consent default is
  the sharper half: granting a consent the contact never gave is a
  **compliance-shaped defect, not an inconvenience**, and it is invisible
  while email is the only channel precisely because the default is always
  right. It stops being right the moment a second channel syncs.
- A device handed to another person with the app still installed and signed in
  will receive push meant for the previous holder. This is **explicitly
  accepted as negligible**: it is not a push-specific problem but the general
  one of somebody holding your unlocked device, which no messaging system
  solves.

## Notes

- **Sequential reassignment of a push token to a different person is not a
  real case, and the mechanism says why.** A token is per-app-install, so a
  wiped and reinstalled device mints a **new** token and the old one simply
  goes dead — which APNs reports, and which
  [[ADR-163 — Per-Channel Consent and Addressability]] point 2's mark-invalid
  path already handles. There is no path by which the platform matches an
  abandoned token to a new owner. The only surviving case is the handed-over
  device covered in `### Negative` above. **ADR-163 needs no addendum for
  this**, and this note exists so the question is not reopened as though it
  were still open.
- This record decides identity, not the sync signature. The second
  `### Negative` item names the gap; the shape of the generalised sync path —
  how channel and address are passed, and what happens to the existing
  callers — is implementation work that follows this decision rather than
  part of it.

## Related ADRs

### Depends On
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-126 — Maintain Local Recipient Projection]]
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
- [[ADR-154 — Erasure and Retention]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]]
