---
id: TASK-260
title: >-
  In the composer, override is the default and editing the catalogue is the
  explicit act — supersedes ADR-178 points 1-3
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:56'
updated_date: '2026-10-03 19:09'
labels:
  - frontend
  - backend
  - needs-adr
dependencies: []
references:
  - docs/architecture/ADR/ADR-178 — Scope of the Correction
  - Not Location of the Manager.md
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: decision
ordinal: 200059
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
User decision, 2026-10-03, after trying slice 6 (task-258) on the dev server: "it's too easy to change the approved content in the catalogue directly. So default should be 'override here' and with a click you can change it in the catalog." This reverses [[ADR-178 — Scope of the Correction, Not Location of the Manager]] points 1-3, which made the catalogue the default ("a typo is wrong everywhere") and override the explicit act. Per CLAUDE.md an accepted ADR's Decision is never edited: this needs a **superseding ADR** (the second supersession in the repo, after ADR-165 superseded ADR-001), drafted through the adr-author agent before the code changes. The rest of ADR-178 (overridden field shown distinctly with the covered value, never on a slot, reset per field and module, duplication carries overrides, reach count, reason presets, no outcome_delta) is not in question and should carry over. Points to settle in the ADR: the reach count (point 8) then belongs to the explicit catalogue edit, shown before it is made; publish state (design pass D5) likewise; whether a field with no override yet types straight into a new override (one per field, as now) or the whole module. Code affected: frontend/src/screens/CatalogueModule.tsx (CatalogueFields), and the docs that describe the current default (design pass D5 wording, the task-258 notes).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A superseding ADR records the new default and what of ADR-178 carries over; ADR-178 marked Superseded in both places
- [x] #2 In the editor a catalogue-bound field edits this module (an override) by default; changing the catalogue record takes an explicit act that shows the unsent-campaign reach first
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ADR-186 (adr-author) supersedes ADR-178; ADR-178 status only, verified as a two-line diff. Done.
2. frontend/src/screens/CatalogueModule.tsx: a field shows its effective value (override, else catalogue); typing saves an override for that field (ADR-186 point 1). Each field gets 'Change in catalogue', which opens a one-field catalogue edit with the reach shown first, an explicit Save to the record and Cancel, then closes (point 2). Overridden fields keep the distinct state, covered value and per-field reset (4, 6).
3. task-261 in the same change: unsaved typing in a field goes where the button points. Moving from the field to its own 'Change in catalogue' does not save an override; the typing opens in the catalogue editor instead.
4. Tests rewritten for the new default; mutation-checked; browser check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. ADR-186 written by adr-author, ADR-178 diff verified as exactly its two status lines. Code: frontend/src/screens/CatalogueModule.tsx: CatalogueField shows the effective value (override, else catalogue); typing saves an override for that field; 'Change <field> in catalogue' opens a one-field act with the reach first, an explicit 'Save to the catalogue' and Cancel, and closes after saving. The two states are keyed apart: without it React reused the opening button's DOM node for 'Save to the catalogue', so the press that opened the act completed on Save and wrote to the catalogue at once (found by the task-261 test; it would have happened in a browser too). An extra 'untouched value' guard was removed after a mutant showed AutosaveField already skips unchanged values. Tests CatalogueModule.test.tsx rewritten (11); mutants: typing edits the record, no hand-off, no keys, no reach first, act stays open: each caught. 98 client tests. Browser on the dev backend: typing in Hero Banner's headline created an override and left record #101 unchanged; the catalogue act showed '1 unsent campaign' before typing; Cancel closed it with the record unchanged; the test override was reset.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Override is now the default in the composer (ADR-186, superseding ADR-178): typing in a catalogue-bound field overrides it for this module, and the catalogue changes only through a per-field 'Change in catalogue' act that shows its reach first and saves explicitly. Verified by rewritten tests, five mutants, and a live check that typing no longer touches the record.
<!-- SECTION:FINAL_SUMMARY:END -->
