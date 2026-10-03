---
id: TASK-251
title: >-
  PUT /campaigns/decision-slots/{id} answers 500 for a config its strategy
  rejects
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
type: bug
ordinal: 100400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Defect 4 of the campaign write surface final-design pass, 2026-10-03. `normalize_slot_config` raises `ValueError` for an undeclared key, a missing required key or a wrong type (`backend/app/decision/strategies/base.py:94`). The PATCH route maps that to 400 (`backend/app/campaigns/router.py:540`); the PUT route calls `update_decision_slot` at `:471` without the mapping, so the same mistake is a 500. The Jinja slot create (`frontend/router.py:1634`) likewise has no try/except, so an unknown strategy there is a 500.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A PUT with a filter or config the strategy rejects answers 400 with the reason
- [ ] #2 The Jinja slot create shows the refusal instead of a 500
<!-- AC:END -->
