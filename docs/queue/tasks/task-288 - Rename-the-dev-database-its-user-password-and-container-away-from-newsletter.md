---
id: TASK-288
title: >-
  Rename the dev database, its user, password and container away from
  'newsletter'
status: To Do
assignee: []
created_date: '2026-10-05 20:04'
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
- [ ] #1 The dev database, role and container carry the agreed names; docker-compose, the fallback URLs and .env.example agree
- [ ] #2 Test databases are created and found under the new name; the user's .env change is confirmed
- [ ] #3 rename_product.py's CANNOT list and the naming decision no longer list the database as an exception
<!-- AC:END -->
