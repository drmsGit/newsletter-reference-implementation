---
id: TASK-259
title: >-
  Every checkout shares one test database, so two suites running at once
  overwrite each other's schema.
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:47'
updated_date: '2026-10-04 16:10'
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
- [x] #1 Two full suite runs started at the same time from two different worktrees both pass, without either setting TEST_DATABASE_URL by hand
- [x] #2 The database a checkout uses is still refused if it is the dev database (_refuse_the_dev_database keeps its guarantee)
- [x] #3 A fresh checkout still needs no setup step to run the suite
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. tests/checkout_database.py: DEV_DEFAULT, checkout_root(), test_database_name(dev_name, root) with slug + hash, length at most 63, [a-z0-9_]; test_database_url() where TEST_DATABASE_URL still wins.
2. conftest: delegates naming; _ensure_database_exists also runs COMMENT ON DATABASE with the checkout path; _refuse_the_dev_database unchanged.
3. scripts/drop_stale_test_databases.py: candidates are <dev>_test and <dev>_test_*; stale = no comment, or the commented path is gone; --drop drops without FORCE and reports failures; never the dev database.
4. Tests: naming unit tests; the guard still refuses the dev name; script stale detection against a throwaway database.
5. Proof for AC1: two full suites at once, from main and a temporary git worktree, both pass. Then remove the worktree and drop its database with the script.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decided with the user 2026-10-04:
1. Every checkout, main included, gets its own test database named <dev>_test_<folder slug>_<6-char hash of the checkout path>. Plain newsletter_test becomes a one-time leftover.
2. Leftovers: the suite records the checkout path as the database comment. scripts/drop_stale_test_databases.py lists test databases whose recorded path is gone (or with none recorded) and drops them only with --drop. Never automatic.

Built 2026-10-04.
- tests/checkout_database.py (new; stdlib only, not collected) names each checkout's database <dev>_test_<folder slug>_<6-hex sha256 of the checkout path>, at most 63 chars. conftest delegates to it and keeps DEV_DATABASE_URL (inside the suite DATABASE_URL already names the test database). On every run it records the checkout path as the database comment; a database named by TEST_DATABASE_URL is recorded with " (named by TEST_DATABASE_URL)".
- The two "endswith(_test)" guards (conftest _build_known_state, test_schema_migrations startup probe) now compare with the exact TEST_DATABASE_URL, which is stricter.
- scripts/drop_stale_test_databases.py lists by default. Stale means: no checkout recorded, recorded checkout gone, or a name the recorded checkout no longer uses. Hand-named databases are never stale. --drop does DROP DATABASE without FORCE, reports refusals, and refuses anything not under <dev>_test.
- Reproduced first: two full suites at once on the shared newsletter_test (main, plus a temporary worktree 10 s later). The worktree run died at load with a Postgres DeadlockDetected while rebuilding the schema under the other.
- Proof for AC1: the same two suites at once with no override, each on its own database: 1248 passed and 1248 passed. The worktree run had INITIAL_ADMIN_EMAIL=admin@example.invalid; see the finding below.
- The script then found the removed worktree's database as gone and dropped it with --drop.
- Incident during mutation testing: the first version of the guard test passed the real dev database name, so the "guard removed" mutant made the test DROP DATABASE newsletter. Postgres refused only because the preview backend held a connection; the dev database was verified intact (115 content_records). The test now uses made-up names that do not exist, so a broken guard can destroy nothing.
- The mutant runs left two mutated-name databases; I dropped them, after which the "name no longer used" rule was added. My reproduction run wrote a hand-named comment onto newsletter_test, which I reset to NULL. newsletter_test (pre-259, listed as stale) and newsletter_migtest (referenced by no code) are left for the user to drop.
- Finding, not fixed (outside AC): a fresh worktree has no .env, so INITIAL_ADMIN_EMAIL is unset and the suite there fails 1 test (test_seed_pending_actions) and skips 9 ("no active admin in this database to act as"). This was the same alone, so it is not a collision. It predates this task and bears on AC3's spirit.
- Tests: tests/test_checkout_database.py (11). Mutation-checked against 12 mutants, each caught. Full backend suite 1248.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Each checkout's suite now runs on a database of its own (<dev>_test_<folder>_<path hash>), created on first use with no setup, so suites in different worktrees no longer rebuild each other's schema. The checkout is recorded on the database, and scripts/drop_stale_test_databases.py lists leftovers and drops them only with --drop. Reproduced the deadlock on the shared database, then proved two simultaneous full suites both pass (1248 each); 11 new tests mutation-checked against 12 mutants; the dev-database guard unchanged.
<!-- SECTION:FINAL_SUMMARY:END -->
