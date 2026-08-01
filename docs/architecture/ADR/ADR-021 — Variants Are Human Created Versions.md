---
type: adr
status: accepted
topic:
  - architecture
  - campaign
  - variant
created: 2026-05-30
modified: 2026-07-31
source:
  - condor-reference-system
  - interview-2026-05-30
  - "AI Layer design interview (Cluster 3 / Q17), 2026-07-31 — granularity-vs-authorship clarification"
depends_on:
  - "[[ADR-020 — Campaign Equals Newsletter]]"
enables:
  - "[[ADR-079 — Dynamic Resolution Outside Builder]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
---


## Status
Accepted

## Context
Newsletter content may differ across audiences, branches, tests or personalization rules.
Not every content difference should become a Builder variant.
Automatic personalization can generate many possible outputs and should not turn the Builder into an uncontrolled black box.

## Decision
A variant is a **deliberately created, reviewable version of a campaign** — never an automatic byproduct of personalization.
Automatic or AI-driven content selection happens **inside** a variant through dynamic slots and the Decision or Rendering Layer; it **never spawns one variant per resolution**. If a slot resolves to 80 different content selections, that is 80 renderings of *one* variant, not 80 variants.
Variants are used when someone deliberately creates, reviews and edits a second version of the same campaign concept. A variant **may be drafted by AI** — what makes it a variant is that it is deliberate and reviewed, not who produced the first draft.

## Consequences

### Positive
- keeps variants editable and understandable
- avoids hidden black-box newsletter generation
- supports A/B testing and branch-specific content versions
- lets marketers adjust known alternatives without developer involvement

### Negative
- can create many variants in complex workflows
- requires clear governance for when to create a variant versus use dynamic content
- dynamic personalization still needs separate architecture

## Notes
A/B test versions are variants. The delivery logic that decides who receives which variant belongs outside the Builder.

**Clarification (2026-07-31).** This ADR constrains **granularity, not authorship.** The title's "human created" has now been misread **twice** — independently — as "AI may not create a variant." It does not mean that. It means *a variant is a deliberate, reviewed version, not one-per-personalization-outcome.* An AI-drafted variant that a human reviews and approves is a perfectly legitimate variant, consistent with [[ADR-082 — AI May Recommend but Not Publish]]. **The file name is kept unchanged for link stability across the ADR set; the Decision section above is the authoritative wording.**

Also considered and rejected (2026-07-31): materializing the N renderings as N real variants now that storage is cheap. It would require a new level (`Campaign → Variant → Version`) purely to distinguish "the human's version" from "what each recipient received" — a distinction **variant vs. resolution/snapshot already draws** ([[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]).

## Related ADRs

### Depends On

- [[ADR-020 — Campaign Equals Newsletter]]

### Enables

- [[ADR-079 — Dynamic Resolution Outside Builder]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
