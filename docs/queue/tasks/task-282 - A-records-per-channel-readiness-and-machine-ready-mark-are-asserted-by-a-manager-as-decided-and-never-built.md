---
id: TASK-282
title: >-
  A record's per-channel readiness and machine-ready mark are asserted by a
  manager, as decided and never built
status: To Do
assignee: []
created_date: '2026-10-04 18:25'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split out of the task-274 design session (2026-10-04): the user chose to keep it out of the content write surface, as its own task. It needs a model change, a migration, the approval path for integrations and its own final-design pass, and the write surface leaves a placeholder for it in each channel section.

**Decided long ago and still unbuilt:**
- [[Manager Workflow - design interview]] Q3 (lines 500-509): push readiness is "asserted by the manager, per channel, like publishing … explicit per-channel state on the content record".
- MW Q3b (lines 519-528): when a required field is emptied, warn and keep the mark.
- [[ADR-174 — Channel Readiness Is Asserted, Not Computed]].
- [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]] point 2: a manager-set "machine ready" flag, a third axis beside `status` and channel readiness.

`content_records` has no column for either (`backend/app/content/db_models.py:9-26`, verified 2026-10-04).

**The approval half is already filed:** task-206 (a content-readiness approvable action plus its `APPROVABLE_ROUTES` entry; MW Q6b, an integration marking a record ready goes through the approval inbox, a person does not). task-206 depends on this task.

**Open for this task's design pass:**
- the shape of the state (one row per channel, or a JSON map on the record);
- what the mark records (who and when);
- how the warning reads when a required field is emptied, given that "required" belongs to a module, not to the record (ADR-177 point 4);
- whether a send or the picker reads it;
- where it shows on the React record page (the placeholder from task-279) and in the Jinja page until that is retired.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A final-design pass settles the shape, recording and warning, and the build follows it
<!-- AC:END -->
