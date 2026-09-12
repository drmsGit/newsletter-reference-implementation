---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - preview
created: 2026-05-30
modified: 2026-09-12
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-060 — Rendering as Independent Layer]]"
---


## Status
Accepted

## Context
Preview rendering, final rendering and snapshot rendering serve different technical contexts.
The Builder preview may use browser-friendly structures, while final email HTML may require nested tables and email-client-specific markup.

## Decision
Require output parity, not necessarily implementation parity.
Preview, final rendering and snapshots should represent the same intended newsletter output.
They may use different technical render implementations if necessary.

## Consequences

### Positive
- allows technical flexibility
- avoids forcing email-client HTML into every UI preview
- keeps final rendering optimized for email clients
- keeps snapshot generation focused on historical stability

### Negative
- differences between preview and final output must be tested carefully
- module changes may need validation across multiple render contexts
- visual parity can be harder than shared implementation

## Notes
Where shared rendering logic is practical, it should be reused. But the architectural requirement is parity of output, not identical code paths.

## Addendum 2026-09-12 — "channel artifact", and parity was always within-channel

Prompted by [[ADR-162 — Channel Rendering and Artifacts]] point 7, which
reread this ADR against the omni-channel question rather than assuming an
answer, and confirmed the parity claim here already generalizes unchanged.

Wording only, no change to the Decision above. Replace "the same intended
newsletter output" with **the same intended channel artifact**. The
substitution is mechanical: this ADR was never about HTML specifically, it
was about preview, final rendering and snapshot rendering agreeing on what
they represent, whatever the rendering implementation. That statement reads
correctly for a push field dict or a letter PDF exactly as it does for email
HTML.

What this addendum clarifies explicitly, because it was implicit before
channel made it worth spelling out: this ADR's parity guarantee was always a
**within-channel** one — between preview, final rendering and the snapshot
of a *single* channel's artifact. It was never a claim about parity *between*
channels. A mock push notification card shown in the Builder versus the JSON
payload actually handed to a push provider is the same preview/final
relationship email already has between browser-friendly markup and
email-client HTML; a letter's on-screen preview versus its print-ready PDF is
the same relationship again. "Parity between an email and a letter" was
never this ADR's goal and is not newly out of scope — it was never in scope.
That question is answered, and rejected, elsewhere: [[ADR-160 — Channel
Model and Composition]]'s decision to give each channel its own variant
(rather than one neutral composition each channel renders its own way) is
what settles that cross-channel sameness is not wanted, not this ADR.

## Related ADRs

### Depends On

- [[ADR-060 — Rendering as Independent Layer]]

### Referenced By

- [[ADR-162 — Channel Rendering and Artifacts]]
