---
id: TASK-137
title: No "deactivate" option for content records — `status` was write-once.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 500100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** **No "deactivate" option for content records — `status` was write-once.** Noticed 2026-07-31 (user, while reviewing content). `ContentRecordDB.status` existed and defaulted to `"active"`, but **no code path could ever change it**: `create_content` and `create_demo_content_if_empty` always wrote `"active"`, and `update_content_record` did not accept or touch `status` at all — so the only way to remove a record was `delete_content_record`, a hard delete. That mattered beyond a missing button: the data-lifecycle Needs-ADR item leans toward *"never hard-delete a content record that has historical usage — archive instead"*, and the 100 placeholder seed records are referenced by module instances, decision resolutions and snapshots, so hard-deleting them would break history. **Done 2026-07-31** — added `set_content_status()` (validated against a deliberately two-value vocabulary, `active`/`inactive`; a richer "archived" notion is left to the data-lifecycle ADR rather than invented here), `PUT /content/{id}/status`, a Deactivate/Reactivate control on the content detail page, and a "Show inactive (n)" toggle on the list (inactive hidden by default). **`update_content_record` deliberately still does not touch `status`** — diverging from this entry's original "let update_content_record set status" wording — so that editing a record can never silently reactivate it. The **module content picker now filters to active only**; the decision strategies already filtered `status == "active"` (`top_score.py:47`, `recipient_top_score.py:85`), so the read side needed no change. Verified live: deactivate → 303 + status flips; record vanishes from the list and the picker (0 occurrences vs 4 for an active control) while staying renderable where already used; invalid status → 422; reactivate restores it. Test suite unchanged at 22 passed / 4 pre-existing failures (verified identical on a stashed tree).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 503, section "Done", position 1 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
