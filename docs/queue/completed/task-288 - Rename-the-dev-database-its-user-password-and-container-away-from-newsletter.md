---
id: TASK-288
title: >-
  Rename the dev database, its user, password and container away from
  'newsletter'
status: Done
assignee: []
created_date: '2026-10-05 20:04'
updated_date: '2026-10-08 22:04'
labels:
  - backend
dependencies: []
type: chore
ordinal: 200105
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided with the user 2026-10-05 (task-29, question 4): the dev database `newsletter`, user `newsletter_user`, password `newsletter_password` and Docker container `newsletter_postgres` keep their names for now, as a listed exception to the product's single source of truth (`product.json`), and are renamed **at a later stage** — the user wants them changed, not now.

**Where they are:** `docker-compose.yml` (container_name, POSTGRES_DB/USER/PASSWORD), the fallback URL in `backend/app/database.py:11` and `backend/tests/checkout_database.py:28`, `backend/.env.example`, and the user's own `backend/.env` (which Claude never reads; the user says it is in step with `.env.example`). The per-checkout test databases are named after the dev one (`tests/checkout_database.py`), and `scripts/drop_stale_test_databases.py` finds them by that name.

**The choice to make first:** name-free (`app`, `app_user`, …) or the slug (`tarrow`). Name-free follows task-29's rule "where a name adds nothing, use none" and survives a second product rename; the slug would need renaming again if the name does not clear.

**What the change involves:** renaming the database and role inside the running Postgres (`ALTER DATABASE … RENAME`, `ALTER ROLE … RENAME`, a new password), with no open connections — so the preview servers stop first; the compose file (a renamed container means recreating it, keep the volume); the two fallback URLs and `.env.example`; the user edits `.env` by hand; dropping the old-named test databases. Back up the dev database before touching it (it holds the user's dev data).

**Also listed in** `backend/scripts/rename_product.py` (`CANNOT`) and `docs/business/decisions/naming-brand-tarrow.md` (2026-10-05 entry); update both when this is done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The dev database, role and container carry the agreed names; docker-compose, the fallback URLs and .env.example agree
- [x] #2 Test databases are created and found under the new name; the user's .env change is confirmed
- [x] #3 rename_product.py's CANNOT list and the naming decision no longer list the database as an exception
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-08: decided, done (commits 7723500, 89cf739; CI green on 7723500).

Verified first. The entry held, with one stale claim: backend/.env.example has no database URL, so the app falls back to the URL in backend/app/database.py. Also unlisted were CI's own database (newsletter_ci) and an orphan database, newsletter_migtest.

Decided with the user one question at a time:
1. Name-free: database app, role app_user, password app_password; CI uses app_ci / app_ci_test. Rejected: the slug tarrow, because the name is provisional.
2. No fixed container name: container_name was dropped from docker-compose.yml, and Compose now names the container per checkout (newsletter-reference-implementation-postgres-1, after the folder, like the volume). Rejected: app_postgres (could clash with another project on the machine) and tarrow_postgres.
3. The user's .env sets neither DATABASE_URL nor TEST_DATABASE_URL (confirmed by the user, not read), so it needed no change.
The user also chose to disconnect DBeaver themselves and to drop newsletter_migtest (an old schema copy: 34 tables, 10 MB, no ledger, used by no code).

Done:
- A full pg_dump backup went to the session scratchpad (43 tables of data). Reference counts beforehand: campaigns 8, recipients 40, audit_events 260.
- The API preview was stopped and DBeaver disconnected, leaving no open connections.
- A temporary superuser renamed newsletter_user to app_user, set its password and renamed the database newsletter to app. It then dropped newsletter_migtest and the old newsletter_test_ database, and was dropped itself.
- docker compose up -d recreated the container on the same volume. The counts afterwards were identical (8 / 40 / 260).
- Logging in with the new credentials over TCP works, and a wrong password is refused.
- In code: docker-compose.yml, the two fallback URLs (app/database.py, tests/checkout_database.py), the example names in test_checkout_database.py, ci.yml, and the exception removed from rename_product.py's CANNOT list.
- The naming decision follow-up was written by adr-author in docs/business/decisions/naming-brand-tarrow.md. That folder is gitignored, so it exists locally only, by design. The playbook entry is committed.

Tests: backend/tests/test_dev_database.py keeps compose and both fallback URLs agreeing and name-free, the container unnamed, and test databases named after the dev one. Mutation check: 4 of 4 caught. The full suite passed (1531) and created app_test_newsletter_reference_implementation_26340f; the folder slug in that name is the repository folder, out of scope. drop_stale_test_databases.py finds it under the new name (1 beside app, 0 stale).

Live check: the API started clean against app, which needs its migration ledger check to pass. The browser session from before the rename was still valid, since sessions live in the database, and the campaign list included the task-52 scratch campaign.

For the user: DBeaver needs the new database app, user app_user and password app_password. Any other checkout or worktree on old code fails to connect until it pulls. The backup dump is in the session scratchpad, which is temporary.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The dev database is now app, with role app_user, renamed in place after a full backup. Data was identical before and after, and CI uses app_ci. The Docker container has no fixed name, so Compose names it per checkout on the same volume. Compose and both fallback URLs agree, and a guard test keeps them name-free. The user's .env needed no change, and the exception left rename_product.py's CANNOT list. Verified by test_dev_database.py (4/4 mutants caught), the full suite (1531 passed, test database created as app_test_), CI green and a live check of the running app.
<!-- SECTION:FINAL_SUMMARY:END -->
