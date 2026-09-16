---
type: adr
status: accepted
topic:
  - architecture
  - content
  - composition
created: 2026-05-30
modified: 2026-09-16
source:
  - condor-reference-system
  - interview-2026-05-30
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
enables:
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
---


## Status
Accepted

## Context
A newsletter may use reusable content from the Content Catalog.
If content is copied into the newsletter at selection time, later catalog updates will not reach active recurring campaigns.
If content is always resolved by reference, centrally maintained content can remain current.

## Decision
Newsletter compositions store references to content records instead of copying the full content into the builder state.
The effective content is resolved during preview or rendering by combining the referenced content with optional overrides.

## Consequences

### Positive
- enables central maintenance of recurring newsletters
- reduces content duplication
- keeps builder data smaller
- makes content usage traceable
- supports the Content Catalog as source of truth

### Negative
- requires reliable content resolution during preview and rendering
- changes in catalog content can affect active campaigns
- usage overview and override visibility become important

## Notes
For sent single campaigns, later catalog updates are usually less relevant because the email is already in the past. For recurring campaigns, central updates are a major benefit. A usage overview should show where a record is used and whether it is used in original or overridden form.

## Addendum 2026-09-16 — the brand boundary is the one place a copy is made

Prompted by [[ADR-150 — Tenancy and Access Model]], which makes a content record belong to exactly one brand. Read alongside this record the two can look like they disagree: this one says compositions reference content and counts "reduces content duplication" as a benefit, while ADR-150 names duplication as the escape hatch for content two brands both need.

They do not disagree. This record predates brands by three months, and it governs *composition* — whether a campaign embeds content text into builder state or points at a catalog record. The brand boundary is a case it never contemplated, not a case it decided differently. The rule that reconciles them: reference wherever referencing is expressible, copy only where the boundary makes it inexpressible.

Within a brand nothing here changes. Duplicating a campaign inside one brand is a copy of structure only — the new modules reference the same content records, and no content rows are created. That is this record working normally rather than an exception to it, and it is the common case. Across a brand boundary, referencing cannot be expressed at all: `ContentRecordDB.brand_id` is NOT NULL, so a brand-B campaign has no way to point at a brand-A record. Copying there is forced, not preferred.

The cost is real and is best stated in this record's own terms. The Context above says copying means "later catalog updates will not reach active recurring campaigns" — that is exactly true of a cross-brand copy, by construction and permanently. A typo fixed in brand A stays wrong in brand B. The Positive list's "reduces content duplication" is deliberately spent here, in the narrowest case available. And the usage overview the Notes ask for matters more rather than less: the provenance of a copy — which record produced which copy — is intended to live in [[ADR-153 — Audit and Accountability]]'s audit log rather than in a column on the copy, and that record is Accepted but not yet built.

One historical note, because it shows the boundary was unenforced until recently. Until 2026-09-16 the campaign page's module content picker offered every brand's content regardless of the campaign's brand, so a manager could bind a brand-A record to a brand-B campaign — referencing across a boundary that referencing cannot express. Only the decision strategies enforced brand on content; the render path did not object. Fixed on 2026-09-16 in `backend/app/frontend/router.py`, where the picker now filters on the campaign's `brand_id`.

Nothing above changes the Decision section. The duplication feature has its own design; this addendum settles only how these two records stand to each other.

## Related ADRs

### Depends On

- [[ADR-010 — Newsletter Content Source of Truth]]

### Enables

- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
