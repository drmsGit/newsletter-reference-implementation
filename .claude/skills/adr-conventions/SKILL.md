---
name: adr-conventions
description: The ADR format, status vocabulary, numbering rules, and
  superseding process used in this repository.
---

# ADR Conventions

Verified against all 94 records on 2026-09-27. Where this file and a habit
disagree, this file wins — but check the reference records before assuming
a record is wrong.

**Counts and the highest number are deliberately not stated below.** Every
figure this file has carried — 82 records, highest 166, "six proposed", then
"two" — was wrong within days of being written, and a stale number in the
document meant to be authoritative is worse than no number. Derive them:
`ls docs/architecture/ADR/` for the count and the highest,
`grep -l '^status: proposed'` for the proposed set.

## Location and filename
`docs/architecture/ADR/ADR-NNN — Title Case Title.md`

- NNN zero-padded to three digits; numbers are permanent, never renumbered or reused.
- The separator is an **em dash surrounded by spaces**, not a hyphen, and the
  title keeps spaces and capitals. Not kebab-case.
- Numbering is sparse, so **the count is never the next number**. Always
  `ls docs/architecture/ADR/`, take the highest, add one — never trust a
  number written in this file or in `CLAUDE.md`.
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
- `## Notes` — used by most records. Not a defect when absent.

**There is no "Alternatives Considered" section in this repository.** No record
has one. Do not add one and do not flag its absence.

## Status vocabulary
- `Proposed` — drafted, not agreed
- `Accepted` — in force
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
The established alternative is a **dated addendum**: a new `##` section
(top level, a sibling of `## Notes` — all 13 addenda in the vault use `##`,
not `###`, and this line said `###` until 2026-09-16)
inside the existing record, headed with its date and what prompted it, leaving
Decision intact. See ADR-101 (addendum 2026-08-02) and ADR-003's
"How this philosophy is realized (2026-07-31 AI-layer interview)".

## Known intentional deviations
- `## Notes` absent in a minority of records — optional, not a defect.
- ADR-130 has no `## Related ADRs` section — the only record without one.
- **No record currently sits at `proposed`** (verified 2026-09-27; ADR-152
  and ADR-166, the last two, were accepted on 2026-09-18 and 2026-09-19).
  Proposed is a real state here rather than a stalled draft, so the set will
  be non-empty again. **Grep for it every time** — this line's count has been
  six, then two, then zero inside three weeks, and each version was written
  as though it would hold.
- **One record has been superseded:** ADR-165 supersedes ADR-001 (2026-09-12).
  It was the first supersession in the repository, so it is still worth saying
  out loud when proposing another.
- ADR-021 has been misread twice as forbidding AI-drafted variants. It
  constrains *granularity*, not authorship.
- ADR-080/081/082 use "AI" to mean model-agnostic ranking; ADR-140–144 use it
  to mean a language model. This ambiguity is logged as an open Needs-ADR
  item, not a drift finding.
