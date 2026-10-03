---
id: TASK-260
title: >-
  In the composer, override is the default and editing the catalogue is the
  explicit act — supersedes ADR-178 points 1-3
status: To Do
assignee: []
created_date: '2026-10-03 18:56'
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
- [ ] #1 A superseding ADR records the new default and what of ADR-178 carries over; ADR-178 marked Superseded in both places
- [ ] #2 In the editor a catalogue-bound field edits this module (an override) by default; changing the catalogue record takes an explicit act that shows the unsent-campaign reach first
<!-- AC:END -->
