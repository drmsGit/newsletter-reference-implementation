---
type: adr
status: accepted
topic:
  - architecture
  - snapshot
  - rendering
created: 2026-05-30
modified: 2026-06-05
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

## Related ADRs

### Depends On

- [[ADR-061 — Snapshot Based Final Rendering]]

### Enables

- [[ADR-053 — Maintain Minimal Delivery Execution History]]
