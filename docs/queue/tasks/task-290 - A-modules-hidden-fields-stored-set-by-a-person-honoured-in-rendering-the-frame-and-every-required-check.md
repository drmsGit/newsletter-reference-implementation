---
id: TASK-290
title: >-
  A module's hidden fields: stored, set by a person, honoured in rendering, the
  frame and every required check
status: To Do
assignee: []
created_date: '2026-10-05 21:27'
updated_date: '2026-10-06 10:45'
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
- [ ] #1 A person sets a module's hidden fields through its own route; an integration is refused
- [ ] #2 Rendering, the frame and a slot's pick leave hidden fields out; old frames render as before
- [ ] #3 The send check, module states and slot candidacy treat a hidden required field as not required
- [ ] #4 Duplication copies the list; a type change prunes it; a re-bind keeps it
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06, the user: hiding and showing are both people only — the route refuses an integration whichever way it would change the list.
<!-- SECTION:NOTES:END -->
