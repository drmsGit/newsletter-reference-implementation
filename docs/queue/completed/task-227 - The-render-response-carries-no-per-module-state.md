---
id: TASK-227
title: The render response carries no per-module state
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-04 07:29'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200062
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The render response carries no per-module state; slot states exist only as HTML comments. A slot that **found nothing** is marked distinctly from one that has not run (4.4) — *the system tried and found nothing* is not *nobody tried*. Identical appearance, different meaning, only one actionable — **and collapsing them trains a manager to ignore both.**

| # | Gap | Where |
|---|---|---|
| 23 | The render response carries no per-module state; slot states exist only as HTML comments | `rendering/router.py` |

Source: [[Variant Editor - design interview]] → What Cluster 4 produced, gap 23 (Q4.4).

**Verified against the code 2026-09-27:** `RenderedVariant` (`backend/app/rendering/router.py:16-28`) holds `variant_id`, `channel`, `role`, `artifact_body` and `fields`. Slot state appears only as HTML comments at `backend/app/rendering/service.py:324` (slot hidden) and `:391` (unknown module).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. module_states(db, variant_id, recipient_id, *, brand_id) in backend/app/rendering/service.py, read-only: per module (envelope excluded) its kind (record / slot / typed / unbound / unknown); for a slot, state resolved / not_run / finds_nothing, where finds_nothing means its rule matches no active content (slot_candidate_count, task-205) and outranks an old resolution, and generic_pick when a named recipient has no resolution of their own (Variant Editor 4.2); for a record, unpublished_changes (publish_state, task-257); required fields left empty (missing_required_fields in preview mode). The slot lookup reuses resolve_content_for_module, so state and render agree.
2. RenderedVariant gains modules: list[ModuleState]; the route answers 404 for a variant outside the brand (it answered 500).
3. Tests per state, mutation-checked.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-04. Built: module_states in backend/app/rendering/service.py and RenderedVariant.modules (ModuleState: kind, slot_state, generic_pick, unpublished_changes, missing_required). 'finds_nothing' is defined read-only as 'the rule matches no active content' (slot_candidate_count), since a strategy that resolves nothing writes no resolution row and so cannot be told from 'not run' by stored data; it outranks an older pick. A per-recipient strategy that finds nothing for one person is not predicted. Also fixed: GET /rendering/variants/{id} answered 500 for a variant outside the brand; now 404. Tests backend/tests/test_module_states.py (6); mutants: no finds_nothing, generic never said, unpublished never said, envelope listed, unbound read as typed, foreign 500: each caught.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The render response now carries each module's state for the composer's preview: kind, the three slot states with 'finds nothing' apart, the generic-pick fallback for a named recipient, unpublished edits, and empty required fields; a foreign variant is a 404. Verified by 6 tests and six mutants.
<!-- SECTION:FINAL_SUMMARY:END -->
