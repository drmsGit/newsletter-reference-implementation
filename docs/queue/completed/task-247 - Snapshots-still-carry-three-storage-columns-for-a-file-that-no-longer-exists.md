---
id: TASK-247
title: Snapshots still carry three storage columns for a file that no longer exists
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 09:47'
updated_date: '2026-10-03 11:28'
labels:
  - backend
dependencies: []
type: chore
ordinal: 209300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Chore]** Found 2026-10-03 when the user asked whether snapshots still have a storage location after ADR-183 point 5 dropped HTML snapshot files. They don't. Every snapshot is written (`backend/app/snapshots/service.py:80-87`) with `artifact_storage_type='inline'`, `artifact_location=INLINE_LOCATION` (the constant 'inline:render_context', kept only because the column is NOT NULL) and `artifact_size` (the byte size of a render computed and thrown away). The dev DB's two snapshots both show exactly that.

The comment at `backend/app/snapshots/service.py:20-22` defers renaming or removing these to 'the open snapshot-storage question'. That question was task-129, answered by ADR-183 and closed, so the columns are leftovers no task tracks. They are returned by the `Snapshot` response model (`backend/app/snapshots/models.py`) and shown by the Jinja campaign page (`backend/app/frontend/router.py:949`, `backend/app/templates/campaign_detail.html:572`, artifact_size).

`render_context` (the frame) stays: under ADR-183 it *is* the snapshot.

Note for the worker: removing a column needs a migration (ADR-181; apply it before further .py edits while a uvicorn --reload server runs). The Jinja page is frozen in its route list, not its template, so dropping the size cell there is allowed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 artifact_storage_type, artifact_location and artifact_size are gone from the Snapshot response, the model and the database (one migration)
- [x] #2 The stale 'open snapshot-storage question' comment is removed
- [x] #3 Nothing that renders or sends a snapshot changes behaviour (suite passes)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-03. Governing: ADR-183 point 5 (no snapshot files; the frame is the snapshot), ADR-181 (migrations are recorded; apply before .py edits while uvicorn --reload runs), ADR-162 point 3 (the 0019 rename, whose test changes meaning).
1. `backend/scripts/migrate_0028_drop_snapshot_artifact_columns.sql`: DROP COLUMN IF EXISTS for the three. Applied to the dev DB first.
2. `backend/app/snapshots/db_models.py`, `models.py`, `service.py`: remove the three columns, the INLINE_LOCATION constant and the stale 'open snapshot-storage question' comment. create_snapshot_for_variant KEEPS its render_frame call: it is the only check that a composition can be laid out, so it refuses a broken snapshot at creation and not at send. Its artifact is just no longer measured.
3. Jinja: drop the size from `backend/app/frontend/router.py:949` and the cell in `backend/app/templates/campaign_detail.html:572` (the route list is frozen, not the markup).
4. Tests: `backend/tests/test_schema_indexes.py` now asserts all six names (html_* and artifact_*) are gone, and that 0028 drops the three, so the two creation paths cannot disagree. `test_click_attribution.py` and `test_frame.py` stop setting the columns (the frameless-snapshot test still covers a pre-ADR-183 row through an empty render_context).
5. Regenerate schema.d.ts (the Snapshot response shrinks).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-03 as planned. `backend/scripts/migrate_0028_drop_snapshot_artifact_columns.sql` was applied to the dev DB before any .py edit (ADR-181 order); the schema check afterwards shows the snapshot table agreeing with the models. create_snapshot_for_variant keeps render_frame as the check that a composition can be laid out, with its output no longer measured. The Jinja snapshot table loses its Size column. Tests: 13 test files had built SnapshotDB with the dropped columns; all were updated. `backend/tests/test_schema_indexes.py` now asserts neither the html_* nor the artifact_* names survive, and that 0028 drops all three (2 mutants caught: a model keeping a column, a migration missing one). Full suite 1056 passed, rc=0; schema.d.ts regenerated, client type-checks. Unrelated, noted for the user: the dev DB has a duplicate plain btree index on delivery_executions.provider_message_id beside the model's unique one (task-164's leftover).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Snapshots no longer carry artifact_storage_type, artifact_location or artifact_size: they're dropped from the database (migration 0028), the model, the API response and the Jinja page. The frame is the snapshot. The render at snapshot time stays, as the check that a composition can be laid out. Verified: schema tests on both creation paths, 2 mutants caught, suite 1056 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
