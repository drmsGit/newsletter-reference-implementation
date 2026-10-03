---
id: TASK-252
title: >-
  No composer write is audited, and an override reset does not record who reset
  it
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 17:08'
updated_date: '2026-10-03 17:47'
labels:
  - backend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: bug
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Defect 5 of the campaign write surface final-design pass, 2026-10-03. [[ADR-153 — Audit and Accountability]] point 4 makes writes the floor. Only the two duplicates are audited today (`backend/app/campaigns/router.py:659`, `:721`). Campaign and variant create, variant edit, module create/update/delete/move, slot create/update and override create/reset write nothing, on either plane. `reset_content_override` (`backend/app/overrides/service.py:158`) sets `active=False` and `reverted_at` and keeps no actor. The pass decided (D2, user 2026-10-03) to keep the hard delete of a module's overrides (`campaigns/service.py:596-600`) and to make the history survive in the audit log instead: override create and reset are audited with the fields and values involved, and a module delete names every override it removed with its `field_overrides`. The override-history screen (Variant Editor interview 3.5) reads the audit log. The pass also chose autosave on blur (D1), so these entries will be frequent; that cost was accepted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each composer write named above records an audit event with the actor and the target, on both planes
- [x] #2 Override create and reset record the fields and values; reset records who reset it
- [x] #3 Deleting a module records every override it removed, with its field_overrides
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Eleven new actions in backend/app/audit/service.py: campaign.created, variant.created, variant.updated, module.created/updated/deleted/moved, decision_slot.created/updated, override.created/reset.
2. Written from the routes with record_from_request (the module's convention; it resolves a person or an integration as the actor), on both planes: backend/app/campaigns/router.py, backend/app/overrides/router.py, backend/app/frontend/router.py. Only after the service succeeded.
3. delete_module returns the overrides it removed (id, field_overrides, active) instead of True, so module.deleted can name them (D2: keep the erase, audit it). None still means not found.
4. Override create/reset carry module_instance_id and field_overrides; the reset's actor is who reset it.
5. Tests: one parametrised test per action per plane asserting the entry (action, subject, actor); mutation-check by removing calls.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Built as planned. 22 new record_from_request calls: JSON 10 (campaigns/router.py: campaign create, variant create/update, module create/update/delete/move, slot create, slot PUT, slot PATCH), overrides/router.py 2 (create, reset), Jinja 12 (frontend/router.py: the same writes plus variant edit and the AI apply-subject, which records applied_suggestion). Shared detail helpers keep both planes identical: module_audit_detail and slot_audit_detail (campaigns/service.py), override_audit_detail (overrides/service.py). module_data is deliberately not in module entries (autosave would log every keystroke's copy); override entries carry field_overrides and reason. delete_module now returns the overrides it erased (None = not found; routes test 'is None'). Tests backend/tests/test_composer_audit.py: 24 parametrised cases (11 writes x 2 planes + slot PUT + apply-subject), each asserting exactly one entry with the plane's actor; plus delete-names-overrides, reset-records-fields-and-actor, refused-write-not-audited. On the original routes 26 of 27 failed (the refused-write guard passes either way). Mutants: Jinja reset unaudited (2 fail), JSON PATCH unaudited (1), delete returning [] (1). Full suite 1153 passed, rc 0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every composer write is now audited on both planes with the actor the plane resolves; an override reset records who reset it and the fields it reverted; a module delete names the overrides it erased (design pass D2). Verified by 27 tests (26 failing on the original routes), three single-call mutants each caught, full suite 1153 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
