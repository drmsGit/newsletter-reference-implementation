---
id: TASK-381
title: Delete the retired email modules at the next full reset
status: Done
assignee:
  - '@claude'
created_date: '2026-10-15 21:04'
updated_date: '2026-10-17 11:39'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Checked 2026-10-17: nothing in the dev database uses single_stack (no module instances, snapshots or delivery records), so the deletion is safe before the demo reset. 2. Delete single_stack.json and .html; section_heading out of fields.json. 3. No module is retired after it, so the retired support goes: ModuleManifest.retired, the manifest key, list_manifests offered filter, the refusal in _refuse_module_type, ModuleManifestOut.retired, the Jinja badge, TestRetired. 4. The source: module mechanism is kept (user, 2026-10-17): its tests run on a manifest the tests declare. 5. Tests using single_stack as an example switch to a live block. 6. Gates; schema regenerated.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Done 2026-10-17 (6ce82c5), ahead of the demo reset: a read-only check of the dev database found no module instance, snapshot or delivery record using single_stack (one image block still holds a stale section_heading value; the demo reset removes it). Deleted: single_stack.json and .html, section_heading from storage/fields.json; the retired support (ModuleManifest.retired and its manifest key, list_manifests offered filter and its three callers, the refusal in _refuse_module_type, ModuleManifestOut.retired, TestRetired), as no other module is retired. Kept by the user's choice: the source: module mechanism; backend/tests/test_module_sourced_fields.py now plants its own block and field definition. Tests using single_stack as an example switched to img_left (test_duplication, test_click_attribution, test_read_models, and the client DeliveryAsSent and CampaignDetail tests); CatalogueModule.test.tsx keeps section_heading in its stand-in manifest, as it tests the kept client mechanism. Left alone: docs/design/CONSTRAINTS.md and canvas-v2/V2Campaigns.dc.html still mention Single Stack; they belong to the parallel design session. Full suite and CI green apart from the unrelated retired-name check in docs/design.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Single Stack, section_heading and the retired-module support are deleted; the per-module field mechanism is kept and tested on a planted block. Safe before the demo reset (nothing in the dev database used it). Verified by the full suite and CI (red only on the unrelated retired-name check).
<!-- SECTION:FINAL_SUMMARY:END -->
