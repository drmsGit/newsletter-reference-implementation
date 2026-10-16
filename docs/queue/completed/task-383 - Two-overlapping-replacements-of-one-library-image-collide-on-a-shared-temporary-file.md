---
id: TASK-383
title: >-
  Two overlapping replacements of one library image collide on a shared
  temporary file
status: Done
assignee:
  - '@claude'
created_date: '2026-10-16 11:31'
updated_date: '2026-10-16 12:31'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Two replacements of the same library image at the same moment collide, and the second fails. `LocalAssetStore.put` in `backend/app/assets/store.py:30-35` writes to `path.with_suffix(".part")` and then renames it over the image. The temporary name depends only on the image's token, so two overlapping writes for one token share one `.part` file: the first rename moves it away, and the second rename raises FileNotFoundError. The image that ends up stored is then whichever write finished first, and the second caller gets an error for a write it believes it made.

Reached through "Replace the file" in the image library (task-112; ADR-197 points 2, 10 and 11). Rare for one person, possible with two managers or a double submit. Found by Codex's regression batch for source 0fd3332a (pre-stage note doc-22, tests-branch commit 7035896, `origin/codex/regression-tests`), which says no promoted task covers it.

**Fix:** give each write its own temporary file in the same directory (for example `tempfile.NamedTemporaryFile(dir=path.parent, delete=False)` or a uuid suffix), then `os.replace` it over the image; remove the temporary file if the write fails. Same-directory keeps the rename atomic. Whether the database row (size, dimensions in `backend/app/assets/service.py` `replace`) can disagree with the bytes when two replacements interleave is worth checking in the final-design pass; last writer wins is acceptable if the row and the file come from the same writer.

**Test:** bring in Codex's `backend/tests/test_asset_write_safety.py` from commit 7035896 (read 2026-10-16). Of its three cases, test_overlapping_replacements_of_one_address_both_finish fails on main today; the other two (a failed disk write keeps the previous image and metadata; another brand's image cannot be replaced, described or hidden) pass. It lands together with the fix, failing first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Overlapping replacements of one image each finish without error
- [x] #2 A failed write leaves no temporary file and keeps the previous image
- [x] #3 Codex's test_asset_write_safety.py is on main and passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-16 (commit 4837703). backend/app/assets/store.py: each put writes its own temporary file, named <token>.<uuid>.part in the same brand folder (so the rename stays atomic), and removes it if writing or renaming fails. backend/app/assets/service.py replace: the image's row is locked (SELECT ... FOR UPDATE) before the file is written and released by the commit, so replacements of one image take turns and the file and the row's size, dimensions and name always come from the same writer. Decided in the final-design pass without asking (internal correctness, no product effect): last writer wins, as before, but consistently. A second replacement waits at most for one write of up to 5 MB.

Codex's backend/tests/test_asset_write_safety.py came in unchanged (its harness patches Path.replace, so the store keeps using Path.replace). Two cases added: a failed write leaves no temporary file and keeps the image; a second replacement waits for the first (a no-wait lock probe from another session is refused while the first writes). First draft of that test deadlocked without the fix, because its probe then held the lock; the probe is rolled back before the writer is released.

Not covered: a process that dies between writing and renaming leaves a stray .part file; nothing reads them (the store serves only exact token paths), and none is cleaned up. No browser check: nothing in the pane changes; the tests run against the real Postgres and a real folder.

Verification: 3 of 5 cases failed before the fix; pytest 1990 passed; Ruff clean; 3 mutations (shared temporary name, no cleanup, no row lock), all caught.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Overlapping replacements of one library image no longer collide: each write uses its own temporary file (removed on failure), and replace locks the image's row so file and row come from the same writer. Codex's test_asset_write_safety.py came in unchanged plus two cases. Verified: 3 cases failed first, pytest 1990, 3 mutations caught, CI green on 4837703.
<!-- SECTION:FINAL_SUMMARY:END -->
