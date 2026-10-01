---
id: TASK-223
title: cms is a boolean — no way to mix resolved fields with one static field
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p3
type: feature
ordinal: 208800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** `cms` is a boolean; no way to mix resolved fields with one static field (`rendering/service.py:162`).

**Gap 14 is the one to look at twice.** The optional heading a slot needs — *"this might be of interest"* — must **hide when the slot hides**, so it cannot be a separate heading module; that would leave it floating above nothing for exactly the recipients [[ADR-086 — Decision Slots Fail Gracefully]] protects. It belongs to the slot-bound module, and the `cms` boolean cannot express it. The storage is already there — the `CHECK` constrains only the two foreign keys, so `module_data` may sit beside a `decision_slot_id` — but the renderer ignores it. This is the second time the cluster found a boolean too coarse; question 1.8 was the first.

Source: [[Variant Editor - design interview]] → What Cluster 2 produced, gap 14.

**Verified against the code 2026-09-27:** the branch is `if manifest.cms:` at `backend/app/rendering/service.py:162`. `resolve_module_variables` (`:257`, variables built at `:299-304`) fills from content plus overrides and never reads `module.module_data`, which is read only on the static path (`:360`) and by the envelope helper (`:195`).

Related: task-108 (the section-heading module, which this is not), task-133 (whether hero / CTA draw from the catalogue).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
