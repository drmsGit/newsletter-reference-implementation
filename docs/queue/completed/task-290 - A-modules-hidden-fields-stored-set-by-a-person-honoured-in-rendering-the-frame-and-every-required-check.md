---
id: TASK-290
title: >-
  A module's hidden fields: stored, set by a person, honoured in rendering, the
  frame and every required check
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 21:27'
updated_date: '2026-10-06 11:01'
labels:
  - backend
dependencies:
  - TASK-289
type: feature
ordinal: 200377
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-218 design interview (2026-10-05, with the user); recorded in [[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]] and [[Element Hiding - final design pass]], decisions 3, 4, 5, 6 and 7 and the pass's own choices. Second of three build tasks; depends on the hideable manifests.

**Build:**
- **Storage:** `module_instances.hidden_fields`, a JSON list of field names, empty by default (migration 0033; run it before any .py edit while the preview reloads, ADR-181).
- **The route:** `PUT /campaigns/modules/{id}/hidden-fields` with `{"hidden_fields": [...]}` and the module's version in `If-Match` (ADR-180 point 2); 403 for an integration (human only, decision 4); 422 for a field the module's manifest does not mark hideable, naming it; audited as a new `module.fields_hidden` action with before and after. The general `PUT /campaigns/modules/{id}` neither carries nor clears it, so the Jinja module form cannot wipe it.
- **Type change and re-bind:** a module-type change keeps only fields the new type still marks hideable; re-binding the record keeps the list.
- **Duplication** copies it (`backend/app/campaigns/duplication.py`, `duplicate_variant`).
- **Rendering leaves hidden fields out before the template** (decision 5): `render_cms_module` and `render_static_module` (`backend/app/rendering/service.py:397`, `:467`), `build_frame` (`backend/app/rendering/frame.py:82`) and `_pick_for_slot` (`frame.py:148`) for a slot's pick at send. The value itself is never touched (decision 7).
- **The frame records `hidden_fields` per module entry**; a frame without the key means none hidden, so old snapshots render as before.
- **Required when shown** (decision 6), through **one helper** every check reads: `missing_required_fields` and `module_states` (`rendering/service.py:484`, `:696`), `missing_required_in_frame` (`frame.py:251`), and `candidate_query` (`backend/app/decision/strategies/base.py`; a field counts if it is required and not hidden in a module the slot fills). The helper sits beside `content.service.fields_a_record_must_fill`.
- `hidden_fields` in the composition and module responses, for the editor.

Tests: each part above, including an integration refused, a stale version refused, a non-hideable field refused, a hidden required headline that no longer blocks a send or a slot candidate, a slot pick at send without the hidden field, an old frame without the key, duplication and type change. Mutation-checked; a live check on scratch data only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A person sets a module's hidden fields through its own route; an integration is refused
- [x] #2 Rendering, the frame and a slot's pick leave hidden fields out; old frames render as before
- [x] #3 The send check, module states and slot candidacy treat a hidden required field as not required
- [x] #4 Duplication copies the list; a type change prunes it; a re-bind keeps it
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Migration 0033 (module_instances.hidden_fields json, default []) applied before any .py edit.
2. Tests first (tests/test_hidden_fields.py): the route (store, version, audit, show again, stale, not hideable, other brand, integration both ways); layout choice (re-bind keeps, type change prunes, duplication copies, composition reports); rendering (left out, value kept; hidden required not missing; frame records the list and freezes shown values; old frame; slot candidacy; the pick at send; a replayed recorded pick).
3. One helper, registry.required_when_shown, read by missing_required_fields, missing_required_in_frame and (through content.service.fields_a_record_must_fill) candidate_query; rendering.service.without_hidden where values reach a template (live email, frame, slot pick, push).
4. campaigns: column, models (ModuleInstance, ComposedModule, HiddenFields), set_hidden_fields + NotHideable, type-change pruning in update_module, the route (404 before 403, people only, If-Match, 422 per field, audit module.fields_hidden), duplication copies.
5. Mutation-check, suites, contract, live check on a scratch campaign.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06, the user: hiding and showing are both people only — the route refuses an integration whichever way it would change the list.

Built as designed. Choices within the design: the route answers 404 for another brand's module before refusing an integration, so a foreign module is indistinguishable from none; an unchanged list writes nothing, moves no version and records no audit entry; the stored list is in manifest order without repeats; render_frame also holds a recorded pick (reconstruction) to the list, in case it was stored before the list existed; the push renderer and the static-module render apply the rule too, though no push or static module marks a field hideable today (so no test can reach those two lines through the standard set — defensive, noted).
Validation: 20 tests, failing first (18 of 19 before the code; the other-brand 404 passed while the route did not exist and stays meaningful); 17 mutants caught; one more ('re-bind clears' as first written) was equivalent — pruning against the same type keeps a valid list — and its real form (clear on a new record) is caught. Backend 1376, client 182 (types regenerated), tsc, contract, schema check (no new debris). Live on scratch campaign 7 'task-290 live check' (variant 13, module 43 bound to scratch record 116): hiding body_medium returned 200; the preview lost the body and kept the headline; button_url was refused 422; the composition reports ['body_medium']; record 116 keeps its body text. Left as is for task-291's live check.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A module in a variant now carries the fields its manager hid (ADR-187): stored in module_instances.hidden_fields (migration 0033), set only by a person through PUT /campaigns/modules/{id}/hidden-fields (version-checked, audited, 422 for a field the manifest does not mark hideable, 403 for an integration either way). Rendering, the frozen send copy and a slot's pick leave hidden fields out while their values stay put; the send check, the editor's module states and slot candidacy treat a hidden required field as not required, through one shared helper. Re-binding keeps the list, a type change prunes it, duplication copies it. Verified by 20 tests, 17 caught mutants, both suites, the contract and schema checks, and a live check on scratch campaign 7.
<!-- SECTION:FINAL_SUMMARY:END -->
