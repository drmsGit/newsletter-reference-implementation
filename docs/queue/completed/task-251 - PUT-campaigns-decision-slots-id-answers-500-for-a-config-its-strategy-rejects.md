---
id: TASK-251
title: >-
  PUT /campaigns/decision-slots/{id} answers 500 for a config its strategy
  rejects
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 17:08'
updated_date: '2026-10-03 17:40'
labels:
  - backend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: bug
ordinal: 100400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Defect 4 of the campaign write surface final-design pass, 2026-10-03. `normalize_slot_config` raises `ValueError` for an undeclared key, a missing required key or a wrong type (`backend/app/decision/strategies/base.py:94`). The PATCH route maps that to 400 (`backend/app/campaigns/router.py:540`); the PUT route calls `update_decision_slot` at `:471` without the mapping, so the same mistake is a 500. The Jinja slot create (`frontend/router.py:1634`) likewise has no try/except, so an unknown strategy there is a 500.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A PUT with a filter or config the strategy rejects answers 400 with the reason
- [x] #2 The Jinja slot create shows the refusal instead of a 500
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. PUT /campaigns/decision-slots/{id} maps the ValueError from normalize_slot_config to 400, as PATCH does.
2. The Jinja slot-create form redirects with ?error= on a ValueError (unknown strategy), as every other composer form does.
3. Tests in backend/tests/test_slot_refusals.py, mutation-checked.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Checked first: slot create over JSON and the Jinja slot edit already mapped the error; only the PUT and the Jinja slot create did not. Reproduced: 3 of 5 new tests answered 500. Mutants: PUT unmapped (2 fail), Jinja unmapped (1). Full suite 1126 passed, rc 0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A slot config its strategy rejects is a 400 with the reason on PUT, and an unknown strategy on the Jinja slot-create form is shown as a refusal, not a 500. Verified by 5 tests (3 reproduced as 500s first), two mutants caught, full suite 1126 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
