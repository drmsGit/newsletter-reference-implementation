---
id: TASK-248
title: >-
  A module can be bound to another brand's content record or decision slot, and
  rendering shows it
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 17:08'
updated_date: '2026-10-03 17:21'
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
- [x] #1 Creating or updating a module with a content_record_id from another brand is refused (400/404), on the JSON route and the Jinja form
- [x] #2 Creating or updating a module with a decision_slot_id from another variant is refused
- [x] #3 The development database is checked for existing cross-brand bindings before the fix, and the result recorded in the notes
- [x] #4 Tests use foreign_brand, and each is mutation-checked
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Checked the dev database first: 28 modules, none bound across brands or to another variant's slot (scratch query), so the fix refuses no existing row.
2. create_module_for_variant and update_module (backend/app/campaigns/service.py) refuse a content_record_id that get_content_record(..., brand_id=) does not find, and a decision_slot_id whose slot is not on the module's own variant. ValueError, which both planes already map (JSON 400, Jinja error banner).
3. Tests in backend/tests/test_module_bindings.py: JSON create and update, Jinja create and edit, foreign_brand record, other-variant slot, with own-brand controls; each mutation-checked.
4. Not in scope: duplication and seed write modules directly (duplication already refuses KEEP across brands, duplication.py:331); rendering's unscoped record lookup (rendering/service.py:567) stays, noted for follow-up.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Dev database checked before the fix (read-only scratch query): 28 modules, none bound to another brand's record or another variant's slot. Fix: _refuse_foreign_binding in backend/app/campaigns/service.py, called by create_module_for_variant (after the variant lookup) and update_module (after the module lookup); a foreign record is 'not found' via get_content_record(..., brand_id=), a slot must be on the module's own variant. Tests backend/tests/test_module_bindings.py (9: JSON create/update, Jinja create/edit, each refusal with an own-brand control). Reproduced first: 6 refusals failed, 3 controls passed. Mutants: record check off (4 fail), slot check off (2), slot check ignoring the variant (2), update path unchecked (3). Full suite 1110 passed, rc 0. Left as is, deliberately: rendering still loads a bound record by id without a brand filter (backend/app/rendering/service.py:567-595). With both write paths closed and duplication refusing KEEP across brands (duplication.py:331), no route can create such a binding; a read-side brand filter would be defence in depth, not offered as a follow-up without the user's say.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A module can no longer bind another brand's content record or another variant's decision slot, on the JSON routes or the Jinja forms; the dev database held no such binding. Verified with 9 tests (6 refusals reproduced as failures first, each with an own-brand control), four mutants each caught, full suite 1110 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
