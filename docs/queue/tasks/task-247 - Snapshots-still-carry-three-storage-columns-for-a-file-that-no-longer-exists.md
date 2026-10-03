---
id: TASK-247
title: Snapshots still carry three storage columns for a file that no longer exists
status: To Do
assignee: []
created_date: '2026-10-03 09:47'
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
- [ ] #1 artifact_storage_type, artifact_location and artifact_size are gone from the Snapshot response, the model and the database (one migration)
- [ ] #2 The stale 'open snapshot-storage question' comment is removed
- [ ] #3 Nothing that renders or sends a snapshot changes behaviour (suite passes)
<!-- AC:END -->
