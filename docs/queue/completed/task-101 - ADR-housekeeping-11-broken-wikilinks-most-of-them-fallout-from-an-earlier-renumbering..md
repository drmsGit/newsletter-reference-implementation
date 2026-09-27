---
id: TASK-101
title: >-
  ADR housekeeping: 11 broken wikilinks, most of them fallout from an earlier
  renumbering.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - docs
  - backend
dependencies: []
type: docs
ordinal: 205400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Docs] — DONE 2026-09-24. ADR housekeeping: 11 broken wikilinks, most of them fallout from an earlier renumbering.** Found 2026-08-02 during a link sweep of the new 150-block ADRs; **the user has scheduled a separate ADR session to clean up and restructure**, so this is the evidence list for that session rather than a task to pick off piecemeal. None of these were introduced by the 2026-08-02 work — every link in ADR-150–154, `MOC - AI Architecture` and `MOC - Security Architecture` resolves.

  **`docs/architecture/Models/Reference Data Model.md` — six links, and they look like a renumbering that this file never followed.** Three of them carry a title that *does* exist, at a different number: `[[ADR-020 — Separate Global and Repeatable Structures]]` (that title is **ADR-030**), `[[ADR-030 — Introduce Override Layer]]` (**ADR-040**), `[[ADR-031 — Override Precedence]]` (**ADR-041**). Those three are mechanical fixes. The other three carry titles that exist nowhere and need someone who knows what they *meant*: `[[ADR-021 — Newsletter Equals Composition]]`, `[[ADR-041 — Campaign as Email-Level Context]]`, `[[ADR-042 — Variants Represent Content Alternatives]]` — the last plausibly meaning today's **ADR-021 — Variants Are Human Created Versions**, but that is a renumber *and* a rename, so it should be confirmed rather than assumed.

  **`ADR-132` — one link, and the stale text misstates the decision.** It references `[[ADR-085 — Decision Resolution Must Be Explainable]]`; the real title is **ADR-085 — Decision Resolution Should Be *Optionally* Explainable**. The rename softened a hard requirement into an optional one, so a reader following the old wording takes away the wrong rule — worth fixing for meaning, not only for the link.

  **`docs/backlog.md` — four shorthand links** that were never full titles: bare `[[ADR-110]]`, `[[ADR-112]]`, `[[ADR-113]]`, and the literal `[[ADR-132 ...]]`. All four targets exist; they just need their real titles.

  **Resolution 2026-09-24.** The six in `Reference Data Model.md` were a
  **rotation, not a shift**: campaign and variant moved down into 020/021, their
  occupants up to 030/031, and those up to 040/041. That reading is confirmed by
  the document's own modelling rules — it has a *"Variant equals Composition"*
  section (so `ADR-021 — Newsletter Equals Composition` meant today's **ADR-031 —
  Newsletter Composition Stores Structure Not Content**) and an *"Overrides are
  Variant-scoped Module Data"* section. The two that "need someone who knows what
  they meant" resolve the same way and were confirmed by the user: `ADR-041 —
  Campaign as Email-Level Context` → **ADR-020 — Campaign Equals Newsletter**,
  `ADR-042 — Variants Represent Content Alternatives` → **ADR-021 — Variants Are
  Human Created Versions**. The competing reading — a uniform +10 shift, making
  them ADR-051/052 — was rejected because those are *delivery* ADRs and every
  other link in that list is content, campaign, variant, override or send
  instance. List re-sorted after repair. `ADR-132`'s own link was already fixed
  by someone before this pass; only the note claiming otherwise was stale.

  **Two findings worth more than the repair.** **(1) Documenting a broken link in
  `[[wikilink]]` syntax creates one.** Half the "broken links in `backlog.md`"
  were this entry quoting the others. They belong in inline code, for the same
  reason `backend/` paths do. **(2) A line-based link check cannot see a link
  split across a line break, and a check that is not code-span aware reports the
  quotes as real.** The sweep that closed this ran over all 2,626 wikilinks in
  the vault with both handled, plus same-file `[[#heading]]` links treated as
  valid: **9 split links** were found and rejoined, 8 of them in
  `AI Layer - design interview.md`, invisible to every earlier pass. One
  non-link was also removed — the MOC wrote the `/interview-prep-baseline`
  **slash command** as a wikilink, which the same file writes as code two
  paragraphs later.

  **Still open, and deliberately not decided here:** whether ADR titles should be stable identifiers at all, given that two renames have now produced dangling links and one changed the meaning of a cross-reference. Options include linking by number with an alias (`[[ADR-085 — …|ADR-085]]`, a pattern already used elsewhere in this file), or adding a link-check to the docs workflow so a rename surfaces immediately instead of years later. Source: link sweep, 2026-08-02.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 283, section "Features", position 54 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
