---
id: TASK-264
title: 'The variant editor, decision slots on their modules (slice 7)'
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-04 07:15'
updated_date: '2026-10-04 07:18'
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
- [ ] #1 A catalogue module can be filled from a new decision slot in one atomic write that states the module version
- [ ] #2 The slot's strategy, categories and strategy settings are edited in place on the module and saved with the slot's version
- [ ] #3 The editor shows how many records the slot would choose between, without resolving it
- [ ] #4 A slot-bound module can go back to a content record
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
<!-- SECTION:NOTES:END -->
