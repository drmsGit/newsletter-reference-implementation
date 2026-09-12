---
type: adr
status: accepted
topic:
  - architecture
  - snapshot
  - rendering
created: 2026-05-30
modified: 2026-09-12
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
enables:
  - "[[ADR-053 — Maintain Minimal Delivery Execution History]]"
---


## Status
Accepted

## Context
A snapshot can be visual, technical or both.
A visual image is useful for support, but it is not enough for link checks, audits, tracking analysis or provider-independent reproducibility.

## Decision
A snapshot stores the final render state.
At minimum, it should include final HTML, resolved content data, content references, overrides, metadata, render timestamp and provider or export metadata where applicable.
A visual preview such as an image may be generated additionally, but it does not replace the technical snapshot.

## Consequences

### Positive
- supports both audit and support needs
- preserves links and metadata
- enables historical HTML inspection
- allows fast visual review if an image preview is generated

### Negative
- larger snapshots than visual-only storage
- additional processing may be needed for visual previews
- retention rules must be defined

## Notes
PNG or image snapshots are service artifacts. Final HTML and resolved data remain the source of truth for the snapshot.

## Addendum 2026-09-12 — "final render state" is a package, not one HTML blob

Prompted by [[ADR-162 — Channel Rendering and Artifacts]] point 3, which
settled what a renderer returns across channels: email needs an HTML body
*and* a plain-text alternative (`multipart/alternative`), push returns a
field dict, and a letter returns a PDF plus an address manifest. None of
these is "a single final render" in the singular sense this ADR's Decision
was written against — email's own need for a plain-text alternative was
already living with a one-artifact constraint rather than being served by
it.

Wording only, no change to the Decision above. Generalize "the final HTML"
to **a package of role-tagged artifacts** — `body_html`, `body_text`,
`address_manifest`, `creative_image` and so on, one or several per snapshot
depending on channel — **with a content hash computed over the whole set**,
not over one member. The hash has to cover the set because hashing only one
artifact (say, the HTML) would leave the others unverified, and they can
diverge from it over time; the hash's job is to let a provider request be
traced back to exactly what was reviewed, and that only holds if every
artifact in the package is covered.

This ADR's job is unchanged: a snapshot stores the final render state, and
that state remains the source of truth over a visual preview. What "final
render state" is made of is simply wider than one HTML blob now — resolved
content data, content references, overrides, metadata, render timestamp and
provider/export metadata still apply per artifact in the set, exactly as the
Decision above already requires for the email case.

## Related ADRs

### Depends On

- [[ADR-061 — Snapshot Based Final Rendering]]

### Enables

- [[ADR-053 — Maintain Minimal Delivery Execution History]]

### Referenced By

- [[ADR-162 — Channel Rendering and Artifacts]]
