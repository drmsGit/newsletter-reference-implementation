---
id: TASK-381
title: Delete the retired email modules at the next full reset
status: To Do
assignee: []
created_date: '2026-10-15 21:04'
labels:
  - backend
dependencies: []
type: chore
ordinal: 210600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
At the next full system reset, delete the email modules ADR-198 retired, and what only they used. Decided by the user on 2026-10-15 during task-371: "keep editorial, retire the rest; keep note that with next full system reset to delete the retired once".

Why not now: a retired module still renders where it is used. Existing variants and frozen snapshots may hold Single Stack, and deleting its manifest would turn those into "unknown module" comments. A full reset removes those variants and snapshots, so the deletion is safe then and only then.

What to delete:
- `storage/modules/email/single_stack.json` and `single_stack.html` (the manifest carries `"retired": true`).
- The `retired` case, if no module carries it any more: the `retired` field and manifest key in `backend/app/modules/registry.py` (`ModuleManifest.retired`, `MANIFEST_KEYS`, `list_manifests(..., offered=True)`), the refusal in `_refuse_module_type` in `backend/app/campaigns/service.py`, `retired` on `ModuleManifestOut` in `backend/app/modules/router.py`, and the `TestRetired` class in `backend/tests/test_block_set.py`. Keep it if another module is retired by then.
- `section_heading` in `storage/fields.json`, if Single Stack is its last user. The tests of the module-typed field mechanism (`backend/tests/test_module_sourced_fields.py`) run on Single Stack since task-371 and need another module with a `source: "module"` field, or go with it.
- `single_stack` in the hideable table test (`backend/tests/test_hideable_fields.py`).
- Stale `section_heading` values left in `module_data` of image blocks (ADR-198 point 5) go with the reset itself.

See [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]] point 5.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Single Stack's manifest and template are gone, and nothing refers to single_stack
- [ ] #2 The retired case is removed from the registry, the add-module refusal and the API, or kept with a stated reason
- [ ] #3 section_heading and its tests are removed or moved to another module-typed field
<!-- AC:END -->
