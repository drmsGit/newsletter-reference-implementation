---
id: TASK-223
title: cms is a boolean — no way to mix resolved fields with one static field
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-04 09:09'
labels:
  - backend
dependencies: []
priority: p3
type: feature
ordinal: 200064
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** `cms` is a boolean; no way to mix resolved fields with one static field (`rendering/service.py:162`).

**Gap 14 is the one to look at twice.** The optional heading a slot needs — *"this might be of interest"* — must **hide when the slot hides**, so it cannot be a separate heading module; that would leave it floating above nothing for exactly the recipients [[ADR-086 — Decision Slots Fail Gracefully]] protects. It belongs to the slot-bound module, and the `cms` boolean cannot express it. The storage is already there — the `CHECK` constrains only the two foreign keys, so `module_data` may sit beside a `decision_slot_id` — but the renderer ignores it. This is the second time the cluster found a boolean too coarse; question 1.8 was the first.

Source: [[Variant Editor - design interview]] → What Cluster 2 produced, gap 14.

**Verified against the code 2026-09-27:** the branch is `if manifest.cms:` at `backend/app/rendering/service.py:162`. `resolve_module_variables` (`:257`, variables built at `:299-304`) fills from content plus overrides and never reads `module.module_data`, which is read only on the static path (`:360`) and by the envelope helper (`:195`).

Related: task-108 (the section-heading module, which this is not), task-133 (whether hero / CTA draw from the catalogue).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Decided 2026-10-04 (user): per-field source. ADR-179 addendum via adr-author.
1. registry: ModuleVariable.source ('content' default, 'module' = typed in the module), declared per (module, field) in the manifest; ModuleVariableOut exposes it.
2. fields.json: section_heading (email, heading, text). img_left, img_right, single_stack declare it optional with source module; their templates render it only when filled; brand.css styles it.
3. rendering: resolve_module_variables fills module-sourced fields from module_data, only when content resolved (a hidden slot hides its heading, ADR-086).
4. overrides refuse module-sourced fields; module_data on a catalogue module accepts only module-sourced fields; content_field_groups and catalogue_fields leave them out.
5. Client: the module's own fields (the heading) edited in place on catalogue and slot modules, saved to module_data with the module's version.
6. Tests, mutants, live check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-04. Backend: ModuleVariable.source (registry, exposed on ModuleVariableOut); section_heading in storage/fields.json and, optional with source module, in img_left / img_right / single_stack, rendered above the module only when filled (brand.css styles it); resolve_module_variables fills module-sourced fields from module_data (only reached when content resolved, so a hidden slot hides its heading); overrides refuse them; a catalogue module's module_data accepts only them; content_field_groups and catalogue_fields leave them out (the pinned field-groups test still passes unchanged). Tests backend/tests/test_module_sourced_fields.py (5); mutants: renderer ignoring the field, field overridable, catalogue module storing content fields, field counted as catalogue: each caught. Tightening found two push tests storing push_title in a catalogue module's module_data, which the push renderer never reads; the dead data was removed. Dev database: no catalogue module holds content keys in module_data. Full suite 1210 passed, rc 0. ADR-179 addendum by adr-author, diff verified 18 added, 0 changed.

2026-10-04. Client: ModuleOwnFields in CatalogueModule edits a catalogue module's own fields (the heading) on record-bound and slot-bound modules, saved to module_data with the module version; content fields filter them out, so no catalogue act or override is offered for them. The label moved into the three manifests ('Heading above this module') and the fields.json note became plain language. Tests CatalogueModule.test.tsx (+2); mutants: heading treated as content, heading missing on slot modules: each caught. 116 client tests; backend 1210 after the manifest edits. Live (backend restarted to load manifests): heading set on Variant 1A's Image Left (slot #1, per-recipient picks); the generic render lacked it (no generic pick, module hidden), the render for noah.36@example.com showed it above 'Winter feature #4'; heading and fence cleared afterwards.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A catalogue module can carry a field typed in the module (ADR-179 addendum, user decision): email's body catalogue modules have an optional heading above them that renders only when the module does, so a slot that finds nothing hides its heading. It is never overridden and never a catalogue field, and the editor offers it on record- and slot-bound modules. Verified by 7 tests, six mutants, and a live render with and without a pick.
<!-- SECTION:FINAL_SUMMARY:END -->
