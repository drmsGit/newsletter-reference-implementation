---
id: TASK-383
title: >-
  Two overlapping replacements of one library image collide on a shared
  temporary file
status: To Do
assignee: []
created_date: '2026-10-16 11:31'
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
- [ ] #1 Overlapping replacements of one image each finish without error
- [ ] #2 A failed write leaves no temporary file and keeps the previous image
- [ ] #3 Codex's test_asset_write_safety.py is on main and passes
<!-- AC:END -->
