---
name: adr-conventions
description: The ADR format, status vocabulary, numbering rules, and
  superseding process used in this repository.
---

# ADR Conventions

Verified against all 82 records on 2026-09-14. Where this file and a habit
disagree, this file wins — but check the reference records before assuming
a record is wrong.

## Location and filename
`docs/architecture/ADR/ADR-NNN — Title Case Title.md`

- NNN zero-padded to three digits; numbers are permanent, never renumbered or reused.
- The separator is an **em dash surrounded by spaces**, not a hyphen, and the
  title keeps spaces and capitals. Not kebab-case.
- 82 records exist; the highest number is **166**. Numbering is sparse —
  count is not the next number. Always take highest + 1.
- `docs/` is an Obsidian vault. Cross-references are wikilinks:
  `[[ADR-101 — Provider Capabilities Are Explicit]]`. Code paths under
  `backend/` are outside the vault — write them as inline code.

## Frontmatter
```yaml
---
type: adr
status: accepted          # lowercase here
topic:
  - governance
created: 2026-06-06
modified: 2026-07-31
source:                   # optional — where the decision was made
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31)"
enables:                  # optional — mirrors the Related ADRs section
  - "[[ADR-140 — AI Capability Layer]]"
---
```

## Required structure
- `## Status` — Title Case value (`Accepted`), must agree with frontmatter
- `## Context`
- `## Decision` — may carry `###` sub-sections
- `## Consequences` — with `### Positive` and `### Negative`
- `## Related ADRs` — with `### Depends On` / `### Enables` / `### Referenced By`

Optional:
- `## Notes` — used by 46 of 82 records. Not a defect when absent.

**There is no "Alternatives Considered" section in this repository.** No record
has one. Do not add one and do not flag its absence.

## Status vocabulary
- `Proposed` — drafted, not agreed (7 records)
- `Accepted` — in force (69 records)
- `Superseded by ADR-NNN` — replaced; the successor must exist
- `Deprecated` — no longer in force, no successor

## Superseding
Never edit an Accepted ADR's Decision section. Write a new ADR, set the old
one's status to `Superseded by ADR-NNN`, and reference the old number in the
new record's Context.

**No record has ever been superseded.** If you are about to be the first, say
so explicitly rather than proceeding quietly — it is more likely the intent
was a dated addendum.

## Amending without superseding
The established alternative is a **dated addendum**: a new `###` sub-section
inside the existing record, headed with its date and what prompted it, leaving
Decision intact. See ADR-101 (addendum 2026-08-02) and ADR-003's
"How this philosophy is realized (2026-07-31 AI-layer interview)".

## Known intentional deviations
- `## Notes` absent in 36 records — optional, not a defect.
- ADR-130 has no `## Related ADRs` section — the only record without one.
- Seven records sit at `proposed`: **ADR-004** (privacy operations, 2026-06-06),
  **ADR-150–154** (security, written and reviewed 2026-08-02) and **ADR-166**
  (inbound machine authentication, 2026-09-13). Proposed is a real state here,
  not a stalled draft. ADR-004 is easy to miss because it sits nowhere near the
  others, and both ADR-150 and ADR-154 depend on it — so the security cluster
  cannot strictly be ratified ahead of it.
- **One record has been superseded:** ADR-165 supersedes ADR-001 (2026-09-12).
  It was the first supersession in the repository, so it is still worth saying
  out loud when proposing another.
- ADR-021 has been misread twice as forbidding AI-drafted variants. It
  constrains *granularity*, not authorship.
- ADR-080/081/082 use "AI" to mean model-agnostic ranking; ADR-140–144 use it
  to mean a language model. This ambiguity is logged as an open Needs-ADR
  item, not a drift finding.
