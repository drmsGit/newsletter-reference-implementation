---
id: TASK-248
title: >-
  A module can be bound to another brand's content record or decision slot, and
  rendering shows it
status: To Do
assignee: []
created_date: '2026-10-03 17:08'
labels:
  - backend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
priority: p1
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by the campaign write surface final-design pass, 2026-10-03 (defect 1), and verified against the code that day. `create_module_for_variant` and `update_module` (`backend/app/campaigns/service.py:478-583`) scope the *variant* or *module* to the working brand, but take `content_record_id` and `decision_slot_id` as given: nothing checks that the record belongs to the same brand, or that the slot belongs to the same variant. Rendering then loads a bound record by id with no brand filter (`resolve_renderable_content`, `backend/app/rendering/service.py:567-595`, called from `resolve_content_for_module` at :637). So a manager holding `campaigns.manage` in brand A can bind brand B's record id into a module and preview, snapshot or send brand B's content. That breaks [[ADR-150 — Tenancy and Access Model]] point 8, which the decision strategies already honour (`decision/strategies/base.py:candidate_query`). Both planes are affected, because the Jinja composer calls the same services. Fixing it first is a precondition of building the React editor on these writes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Creating or updating a module with a content_record_id from another brand is refused (400/404), on the JSON route and the Jinja form
- [ ] #2 Creating or updating a module with a decision_slot_id from another variant is refused
- [ ] #3 The development database is checked for existing cross-brand bindings before the fix, and the result recorded in the notes
- [ ] #4 Tests use foreign_brand, and each is mutation-checked
<!-- AC:END -->
