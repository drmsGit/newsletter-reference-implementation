---
id: TASK-259
title: >-
  Every checkout shares one test database, so two suites running at once
  overwrite each other's schema.
status: To Do
assignee: []
created_date: '2026-10-03 18:47'
labels:
  - backend
dependencies: []
references:
  - backend/tests/conftest.py
type: bug
ordinal: 104500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every worktree and the main checkout run the suite against the same database: `_test_database_url` (`backend/tests/conftest.py:40`) derives `<dev>_test` — `newsletter_test` — from `DATABASE_URL` unless `TEST_DATABASE_URL` is set, and nothing sets it per checkout. The suite is destructive by design: `_start_from_an_empty_schema` (`backend/tests/conftest.py:104`, called at load on line 148) drops and recreates the `public` schema, and `_build_known_state` (`backend/tests/conftest.py:171`) runs `Base.metadata.drop_all` / `create_all` and reseeds (line 219). A second run started while the first is in flight rebuilds the schema underneath it — from *its own* checkout's models, which may differ.

**Seen on 2026-10-03, not theoretical.** While verifying the conftest fix for collection-time `UndefinedColumn` (commit 2bb8b8b), a throwaway column `zz_probe_column` was added to `ContentRecordDB` in one worktree. The first full run collected cleanly, then failed partway through — 86 failed, 201 errors — with `UndefinedColumn: column "zz_probe_column" of relation "content_records" does not exist`. Nothing in the suite drops tables mid-run, and no other pytest was running when checked afterwards; the likeliest explanation is another session running the suite on the same `newsletter_test` from a checkout without the column. The next three runs were clean. Not proven, but the mechanism needs nothing exotic: with several Claude sessions working in parallel worktrees, concurrent suites are the normal case.

**This predates the 2026-10-03 change.** The old autouse `_known_state` fixture ran the same `drop_all` / `create_all` at session start, so concurrent runs could already clobber each other; the load-time schema reset only moved the moment it happens.

The cost is the worst kind for a harness: failures that belong to someone else's run, appearing in yours, intermittently — which invites re-running until green, or rewriting tests to tolerate drift (the exact damage the 2026-07-31 entry that created the test database set out to undo; see the `_build_known_state` docstring).

`TEST_DATABASE_URL` already exists as the override and `_ensure_database_exists` already creates a missing database on first use, so a per-checkout name may need little beyond deriving it — but the derivation, and what happens to databases left behind by deleted worktrees, are open.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Two full suite runs started at the same time from two different worktrees both pass, without either setting TEST_DATABASE_URL by hand
- [ ] #2 The database a checkout uses is still refused if it is the dev database (_refuse_the_dev_database keeps its guarantee)
- [ ] #3 A fresh checkout still needs no setup step to run the suite
<!-- AC:END -->
