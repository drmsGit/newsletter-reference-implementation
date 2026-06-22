---
type: adr
status: accepted
topic:
  - architecture
  - content
created: 2026-05-30
modified: 2026-06-05
source:
  - condor-reference-system
  - interview-2026-05-30
enables:
  - "[[ADR-011 — Store Reusable Content Only]]"
  - "[[ADR-012 — Content Records Represent Communication Units]]"
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
---


## Status
Accepted

## Context
Newsletter content needs a reliable source from which reusable content, metadata, media and categorization can be resolved.
This source may be a dedicated Content Catalog or an external CMS.
However, many existing CMS structures are not optimized for newsletter composition, automation or AI-supported content selection.

## Decision
The architecture requires a newsletter-ready content source of truth.
It may be implemented as a dedicated Content Catalog or provided by an external CMS, as long as the content structure, metadata, categorization and access patterns are suitable for newsletter use cases.

## Consequences

### Positive
- creates a reliable source for reusable newsletter content
- reduces duplicated content
- supports content governance
- enables future automation and AI recommendations
- keeps newsletter-specific metadata close to the content

### Negative
- may require dedicated development effort
- external CMS integrations must be evaluated carefully
- content synchronization can become necessary when other systems also need the content

## Notes
If an existing CMS has a rigid structure optimized for other systems, a dedicated newsletter content system may be preferable. Pushing selected newsletter content into the external CMS can be less harmful than forcing newsletter logic into an unsuitable CMS model.

## Related ADRs

### Enables

- [[ADR-011 — Store Reusable Content Only]]
- [[ADR-012 — Content Records Represent Communication Units]]
- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
