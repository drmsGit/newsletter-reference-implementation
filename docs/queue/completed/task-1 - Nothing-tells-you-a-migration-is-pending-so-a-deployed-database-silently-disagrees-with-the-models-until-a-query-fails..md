---
id: TASK-1
title: >-
  Nothing tells you a migration is pending, so a deployed database silently
  disagrees with the models until a query fails.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 14:19'
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

Decided and built 2026-09-29. Option B of three, chosen by the user: a schema_migrations ledger plus an explicit runner, over a startup schema check alone (cannot see data migrations — a database missing 0020 passes a column diff) or Alembic (reverses CODE-REVIEW-BRIEF's argument against a generated chain). ADR-181, drafted by the adr-author agent (f596a0c); implementation ea8283a.

Startup refuses while any migrate_*.sql / migrate_*.py in backend/scripts/ has no ledger row, naming the files and the command. scripts/migrate.py: status by default, --apply runs pending in order and stops at the first failure, --baseline records an existing current database only after check_schema agrees. Rows carry how: ran / baseline / built.

Found by the tests during the build: (1) pkgutil.walk_packages missed six tables because app/content and app/providers are namespace packages — replaced by a filesystem walk, with a test comparing it to importing main in a fresh process; (2) the first runner set autocommit on SQLAlchemy's pool proxy, which silently did nothing, so every SQL file rolled back while recorded as ran — now an explicit commit/rollback. 14 ledger tests; 7 mutants, all caught, including removing the startup call from main.py (tested at the call site in a subprocess).

The dev database was baselined on 2026-09-29: check_schema agreed and both data migrations had been run by hand that week. 702 tests pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A database now records which migrations it has had (schema_migrations, ADR-181), and the application refuses to start while one is pending, naming the file and the command. Applying stays a person's act via scripts/migrate.py. Verified by 14 new tests with 7 mutation checks, a call-site test that imports main in a fresh process against a database missing one row, and baselining the dev database, which then boots.
<!-- SECTION:FINAL_SUMMARY:END -->
