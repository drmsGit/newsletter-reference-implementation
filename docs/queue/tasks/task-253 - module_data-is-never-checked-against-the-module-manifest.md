---
id: TASK-253
title: module_data is never checked against the module manifest
status: To Do
assignee: []
created_date: '2026-10-03 17:08'
labels:
  - backend
  - frontend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: bug
ordinal: 100600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Defect 7 of the campaign write surface final-design pass, 2026-10-03 (defect 6, deleting a module erases its overrides, was settled as audit-not-schema and folded into the audit task). `module_data` is stored as whatever dict the caller sends, on create and update (`backend/app/campaigns/service.py:536-543`, `:579`). Overrides already refuse keys the manifest does not declare (`backend/app/overrides/service.py:75-86`); module data does not. Per [[ADR-177 — A Field Is Defined Once, Required Per Module]], `required` and lengths stay advisory while editing (completeness is shown in the editor, VE 2.2), but an undeclared key or a value of the wrong type is a defect. The React editor will generate its form from `GET /modules` (`ModuleVariableOut`), so the server is the only place a wrong key can be stopped. On the client side, `read()` (`frontend/src/api/resources.ts:65-74`) keeps only a string `detail`, so FastAPI's per-field 422 list never reaches a form.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 module_data with a key the manifest does not declare, or a value of the wrong declared type, is refused with the field named
- [ ] #2 A missing required field or an over-length value is still accepted
- [ ] #3 The development database is checked for stored module_data the new rule would refuse, before the fix
- [ ] #4 The client carries 422 field errors to the form that sent them
<!-- AC:END -->
