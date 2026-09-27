---
id: TASK-132
title: >-
  `backend/tests/conftest.py` redirects the suite to `newsletter_test`, creates
  it on first use, drops and rebuilds the schema from the models, and seeds a
  known state — then refuses to run at all if i…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
ordinal: 301600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **Done 2026-09-19 — an isolated test database, and it is NOT an ADR.** `backend/tests/conftest.py` redirects the suite to `newsletter_test`, creates it on first use, drops and rebuilds the schema from the models, and seeds a known state — then refuses to run at all if it resolves to the development database. Recorded as a convention in `docs/architecture/Code/testing.md` rather than an ADR, the same call made for the reference deployment: how tests get a database is tooling, but the rule it enforces — *a test owns its data; the test database is disposable* — shapes every future test. **SQLite was considered and rejected**, for a reason worth not re-litigating: the partial unique index on content overrides silently becomes a full one there, so behaviour changes quietly instead of loudly. The residual weakness this entry named is closed too — `test_overrides.py`'s module-level `pytest.skip` is now an `AssertionError`, so an emptied database fails loudly instead of making thirteen tests vanish during collection. **Running the seed against an empty database for the first time immediately found it had rotted twice** against the schema: consent events with no `brand_id`, and variants built with `subject=`/`preheader=` columns that migration 0012 dropped. Original text follows. ---  Surfaced 2026-07-31 while repairing 4 pre-existing failures (see Done archive). Every failure came from tests coupling to a mutable shared database: hardcoded seed ids that were deleted during normal campaign building, and assertions on seeded signal values that **decay in real calendar time** (a seeded 90 reads 37 a month later with nothing broken). The tests were fixed to be drift-tolerant — resolve fixtures by shape, create throwaway fixtures, assert on deltas rather than absolutes — but that treats the symptom. **A truncate-and-reseed would NOT be the fix:** it makes failures vanish until the next deletion or the next month, it cannot touch the SQLAlchemy metadata/import-order defect at all, and here it is actively unsafe because the dev database also holds real work (imported content, campaigns, live engagement signals). **What would actually solve it:** a dedicated test database (or per-test transaction rollback), so tests get a known state, reseeding becomes safe, and assertions can be absolute again. **Known residual weakness in the current fix:** `_find_module` in `tests/test_overrides.py` calls `pytest.skip(allow_module_level=True)` when nothing matches, so a sufficiently emptied database would make the module skip **silently** rather than fail — a silent skip hides regressions as effectively as a broken test. Ties to: `tests/test_overrides.py`, `tests/test_signals.py`, `backend/scripts/reset_all_data.sql`. Source: user, 2026-07-31 ("would a truncate and reload standard test seed data have solved this?").
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 465, section "Needs ADR", position 16 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
