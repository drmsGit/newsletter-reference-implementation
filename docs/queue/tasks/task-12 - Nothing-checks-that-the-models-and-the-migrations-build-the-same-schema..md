---
id: TASK-12
title: Nothing checks that the models and the migrations build the same schema.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 14:19'
labels:
  - backend
dependencies: []
priority: p3
type: chore
ordinal: 101200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — P3, and it is the gap that let the index drift exist.** **Nothing checks that the models and the migrations build the same schema.** A test database comes from `Base.metadata.create_all`; a deployed one comes from `backend/scripts/migrate_*.sql`. When they drifted once before, `pending_actions` lost its partial unique index and two tests passed against a database that could not have refused them. `tests/test_schema_indexes.py` (2026-09-20) does the narrow version for migration 0018's three indexes; the general check — build a database both ways and diff the schemas — is a bigger piece of work and does not exist.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 60, section "Bugs", position 12 in that section (top = do next). The description is the original entry, verbatim.

2026-09-29: now much cheaper. ADR-181's runner (scripts/migrate.py, app/schema_migrations.apply_pending) applies migration files in order and stops at the first failure, which is the half this task needs. Caveat recorded in ADR-181: several old migrations assume a populated database (0012 encodes a dev row count), so replaying from empty may need a seed step or a cut-over baseline point rather than migrate_0001a.
<!-- SECTION:NOTES:END -->
