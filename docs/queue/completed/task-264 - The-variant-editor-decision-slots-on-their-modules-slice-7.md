---
id: TASK-264
title: 'The variant editor, decision slots on their modules (slice 7)'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 07:15'
updated_date: '2026-10-04 07:21'
labels:
  - frontend
  - backend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200061
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Slice 7 of [[Campaign Write Surface - final design pass]], started 2026-10-04. Variant Editor interview 1.3: a slot is configured on its module, in place ("shape A"); the manager supplies the strategy and its settings (decision_strategy, candidate_filter, strategy_config), and an optional "what would be selected now" summary is welcome but not a commitment; the Decisions screen becomes a management and reuse surface, not where slots are created. ADR-186 point 5 (from ADR-178): a slot-bound module is never overridden. max_results is dead configuration (task-109), so the editor does not offer it. Today a module can be bound to an existing slot only through a raw PUT, and creating one plus binding it is two writes with an orphan slot when the second fails.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A catalogue module can be filled from a new decision slot in one atomic write that states the module version
- [x] #2 The slot's strategy, categories and strategy settings are edited in place on the module and saved with the slot's version
- [x] #3 The editor shows how many records the slot would choose between, without resolving it
- [x] #4 A slot-bound module can go back to a content record
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend: POST /campaigns/modules/{module_id}/decision-slot with If-Match on the module: creates a slot on the module's variant (top_score unless given; name from the module), binds the module to it, one transaction; audited as decision_slot.created and module.updated. Refuses a non-catalogue module.
2. Client hooks: useStrategies, useCategories, useAttachSlot (module queue), useSaveSlot (PATCH, slot If-Match from the composition's decision_slots, own queue), reuse useSlotCandidates and useBindModule.
3. CatalogueModule: an unbound module offers "Use a content record" or "Personalise with a decision slot"; a slot-bound module shows SlotSettings: strategy choice, category checkboxes, the strategy's declared config fields, candidate count, link to the slot screen, and "Use a content record instead".
4. Tests, mutants, live check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-04. Backend half: attach_new_slot in backend/app/campaigns/service.py and POST /campaigns/modules/{module_id}/decision-slot (If-Match on the module; creates the slot with the strategy's defaults, binds the module, clears its record, one transaction; audited decision_slot.created and module.updated; refuses a static module or an unknown strategy with nothing left behind). Tests backend/tests/test_attach_slot.py (6); mutants: no version check, static allowed, record kept, no brand scope, slot creation unaudited: each caught. Full suite 1188 passed, rc 0.

2026-10-04. Client half: hooks useStrategies, useCategories, useAttachSlot (module queue, module If-Match), useSaveSlot (PATCH with only the changed section, slot If-Match read from the cached slot read at send time, own queue; invalidates the slot reads and the composition). screens/SlotSettings.tsx: strategy choice, category checkboxes (none = every category), the strategy's declared number settings saved on blur (non-numbers refused in place), the candidate count from task-205, a link to the slot screen; max_results not offered (task-109). CatalogueModule: a slot-bound module shows SlotSettings and 'Use one content record instead'; an unbound one offers the record search or 'Personalise with a decision slot'. Tests SlotSettings.test.tsx (6) against a stub that checks the slot version; mutants: strategy change resending everything, a non-number saved, no slot token, attach without token, no candidate count, no way back to a record: each caught. 104 client tests, tsc clean. Browser on the dev backend (Variant 1A, Image Left, slot #1): settings render with 85 candidates; ticking Wildlife saved category 14 and the count became 89; unticking restored the original filter exactly; both saves moved the slot version, no conflict. The backend had been stopped by the app overnight and was restarted; my pane signed in again with the dev account.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Decision slots are now set up on their modules: a catalogue module can be filled from a new slot in one atomic write, the slot's strategy, categories and settings are edited in place with its version, the editor shows what the slot would choose between, and a slot-bound module can go back to one record. Verified by 12 tests (backend and client), eleven mutants, and a live round trip on slot #1.
<!-- SECTION:FINAL_SUMMARY:END -->
