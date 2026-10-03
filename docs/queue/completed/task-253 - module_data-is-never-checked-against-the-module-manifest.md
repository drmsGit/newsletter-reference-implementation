---
id: TASK-253
title: module_data is never checked against the module manifest
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 17:08'
updated_date: '2026-10-03 17:52'
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
- [x] #1 module_data with a key the manifest does not declare, or a value of the wrong declared type, is refused with the field named
- [x] #2 A missing required field or an over-length value is still accepted
- [x] #3 The development database is checked for stored module_data the new rule would refuse, before the fix
- [x] #4 The client carries 422 field errors to the form that sent them
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Dev database checked first (read-only): 14 modules with module_data, none with an undeclared key or a non-text value.
2. backend/app/campaigns/service.py: _refuse_module_data on create and update; ModuleDataInvalid(ValueError) carries every bad field. Missing required, None and long values stay accepted (ADR-177).
3. backend/app/campaigns/router.py: the module routes answer ModuleDataInvalid with a 422 in FastAPI's own validation shape (loc body/module_data/<field>); the Jinja forms show the message unchanged.
4. frontend/src/api/session.ts: HttpError.from(status, detail) keeps a string detail, and turns a validation list into fields (field -> message) plus a joined detail; read() in resources.ts uses it.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Backend commit b77fe5f: 7 tests in backend/tests/test_module_data.py, 5 reproduced as failures first; mutants (undeclared allowed 4 fail, any type 2, update unchecked 1, 400 instead of 422 3, None refused 1). Full suite 1160 passed, rc 0. Client: 3 HttpError.from tests in session.test.tsx and a Settings test proving a list detail reaches the screen through read(); mutants (read() dropping lists, no field map) each caught; 75 client tests, tsc clean. The contract check also caught that the task-252 commit shipped schema.d.ts one docstring stale (the override reset route's description); regenerated and committed here.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
module_data now holds only its manifest's fields as text, refused per field with a 422 in FastAPI's validation shape (Jinja shows the message); missing required fields stay allowed per ADR-177. The client carries 422 field lists into HttpError.fields and a readable detail. Verified by backend and client tests reproduced first, seven mutants caught, 1160 backend and 75 client tests, contract check clean.
<!-- SECTION:FINAL_SUMMARY:END -->
