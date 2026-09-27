---
id: TASK-133
title: >-
  Should hero / CTA (and any future module type) draw from the content catalogue
  like cms modules do?
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - needs-adr
  - backend
dependencies: []
ordinal: 301700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Should hero / CTA (and any future module type) draw from the content catalogue like cms modules do?** Surfaced 2026-07-31 (user), while reviewing why a test hardcoded the field `headline` — a `hero` field that does not exist on cms modules, which use `headline_medium`. **Today:** cms modules (img_left/img_right) bind a `content_record_id`, so their copy is catalogue content — categorised, versioned, overridable, attributable. `hero` and `cta` are typically filled from raw `module_data` instead, so their copy lives nowhere in the catalogue. Modules *can* already reference content records regardless of type, so the gap is convention plus per-type field naming, not a missing capability. **Why it may be worth changing — the strongest driver is AI, not tidiness:** a company that will not let AI *write* content but will let it *assemble* a campaign (consistent with [[ADR-082 — AI May Recommend but Not Publish]]) needs **every slot to be selectable from the governed catalogue**. While hero and CTA sit outside it, a "fully AI-composed campaign" is impossible by construction — there will always be human-authored holes the decision engine cannot fill. Same argument extends the decision engine itself: it could pick a hero or a CTA, not only body modules. **Secondary benefits:** consistent field naming across manifests; click attribution on hero/CTA (the DOI/cold-start item above already needs fixed content linked to content records, and this generalises it); categorisation stays optional (a record with no category assignments simply never wins a category-driven pick). **Refinement (user, 2026-07-31) — the hard case is not CTA, and existing ADRs mostly draw the line already.** **A CTA always links to something specific**: it pulls its text from the linked content record, and where that text does not fit the context the manager uses the **override** function (exactly what [[ADR-040 — Introduce Override Layer]]/[[ADR-041 — Override Precedence]] exist for). Even a bare "visit our homepage" could be one general catalogue piece — and in practice there is always some context to link with. Hero behaves the same way. **The genuinely tricky case is a standalone headline module used to separate parts of an email** ("Deals", "This week") — it carries no message and no angle.
  That case is already answered by the ADRs, and in the opposite direction: [[ADR-012 — Content Records Represent Communication Units]] says a content record is a *communication unit — a specific message or content angle*, which a section divider is not; and [[ADR-031 — Newsletter Composition Stores Structure Not Content]] says composition owns *structural assembly*. So **a divider headline correctly stays in `module_data`; it is structure, not content.**
  **This also dissolves the AI capability ceiling above:** AI fills every *content* slot from the catalogue, while structural slots come from the composition/template and were never its job — so a fully AI-assembled campaign stays possible without putting dividers in the catalogue.
  **The [[ADR-011 — Store Reusable Content Only]] tension is therefore smaller than first assumed** — a hero or CTA promoting a specific thing is a communication unit even when used once.
  **What is left to decide:** (a) **field naming** — normalise variable names across manifests, or let content records carry a superset each manifest maps from (the user's "hero pulls single-stack info" vs "company adds extra if-hero fields"); (b) whether **structural modules become a recognised class** (divider/spacer/section-heading) so "every content slot is fillable, structural slots are not content" is stated rather than implied; (c) whether content-bearing module types keep a raw-`module_data` escape hatch at all, given the override layer already covers context mismatch. **The user wants to walk the relevant ADRs before settling this.** Ties to: [[ADR-011 — Store Reusable Content Only]], [[ADR-012 — Content Records Represent Communication Units]], [[ADR-013 — Content Reference Instead of Content Copy]], [[ADR-031 — Newsletter Composition Stores Structure Not Content]], [[ADR-040 — Introduce Override Layer]], [[ADR-131 — Email Module Templates Use MJML as Source Format]], the manifest/variables contract, and the DOI cold-start item. Source: user, 2026-07-31.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 467, section "Needs ADR", position 17 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
