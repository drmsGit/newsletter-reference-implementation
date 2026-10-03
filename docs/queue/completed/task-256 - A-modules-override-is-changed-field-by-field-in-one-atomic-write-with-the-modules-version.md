---
id: TASK-256
title: >-
  A module's override is changed field by field in one atomic write, with the
  module's version
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:27'
updated_date: '2026-10-03 18:30'
labels:
  - backend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200056
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Slice 6 of [[Campaign Write Surface - final design pass]] (2026-10-03). [[ADR-178 — Scope of the Correction, Not Location of the Manager]] point 2 makes override a per-field state ("override here" converts one field) and point 6 resets per field ("removes that key; if the dict empties, the row deactivates") and per module. The API has only create (refused while an override is active: "reset it before adding a new one", `backend/app/overrides/service.py:133-143`) and a whole-row reset, so overriding a second field or resetting one field takes reset + create: two transactions, a window with no override, a changed override id, and no version check, so two editors silently overwrite each other (ADR-180).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 One write sets a module's override fields to a given set: creates the override when none is active, changes it in place when one is, deactivates it when the set is empty; keys checked against the manifest; refused for a slot-bound module
- [x] #2 It takes If-Match with the module's updated_at and moves that version, so a stale override write is a 409
- [x] #3 It is audited (created, changed or reset, with the fields and values)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. set_override_fields in backend/app/overrides/service.py: locks and checks the module's version (refuse_stale, renamed public in campaigns/service.py), reuses the slot and manifest-key checks, then creates, changes in place or deactivates the one active override, and moves module.updated_at.
2. PUT /overrides/modules/{module_id} (overrides.manage by the /overrides/ prefix) with If-Match; audit override.created / override.changed (new) / override.reset.
3. Response: the live override and the module's new updated_at.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Tests backend/tests/test_override_fields.py (6): set/add/reset-one/reset-all with the row kept and its id stable, version covers the override (stale 409), undeclared key refused, slot-bound refused, foreign brand 404, audit actions in order. 5 failed on the old code (no route); the foreign-brand test passed trivially until mutant M6 (no brand scope) proved it. Mutants: no version check, version not moved, reset deletes, change recreates, slot allowed, no brand scope: each caught. Full suite 1174 passed, rc 0. Client types regenerated. The old create and reset routes stay for existing callers.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
One write, PUT /overrides/modules/{id}, now sets a module's overridden fields: creates, changes in place or resets the override atomically, checks and moves the module's version, refuses slot-bound modules and undeclared keys, and is audited per outcome. Verified by 6 tests and six mutants, full suite 1174 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
