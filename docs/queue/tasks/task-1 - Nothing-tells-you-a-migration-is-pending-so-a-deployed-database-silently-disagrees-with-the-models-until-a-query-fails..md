---
id: TASK-1
title: >-
  Nothing tells you a migration is pending, so a deployed database silently
  disagrees with the models until a query fails.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P1 in cost, and it already cost a morning. Found the hard way 2026-09-20.** **Nothing tells you a migration is pending, so a deployed database silently disagrees with the models until a query fails.** `migrate_0019` renamed three `snapshots` columns; the models were updated, the suite passed, and the dev database was not migrated — so every query touching snapshots raised, including the one the dashboard runs on sign-in. **Signing in returned a 500 and the cause was four layers from the symptom.** The test suite cannot catch this by construction: it rebuilds its own database from the models on every run and deliberately refuses to connect to any other, so it is green whatever a deployment looks like. `tests/test_schema_indexes.py` asserts the migration FILE says the right thing, which is a different claim. **Partly mitigated:** `backend/scripts/check_schema.py` diffs models against whatever database it is pointed at and exits non-zero — a detector, not a runner, because a script that silently `ALTER`s a database holding real work is a worse failure than the one it prevents. **Still open:** nothing RUNS it, and nothing records which migrations a given database has had. The honest fixes are a `schema_migrations` table plus a runner, or Alembic — which `CODE-REVIEW-BRIEF.md` lists as a deliberate omission, and this is the bill for it. Take that decision consciously rather than by attrition.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 25, section "Bugs", position 1 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
