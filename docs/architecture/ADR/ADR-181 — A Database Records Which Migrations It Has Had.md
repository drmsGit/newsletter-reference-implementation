---
type: adr
status: accepted
topic:
  - architecture
  - governance
created: 2026-09-29
source:
  - "task-1, decided by the user 2026-09-29: option B of three"
depends_on:
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
---

## Status
Accepted

## Context

Migrations live in `backend/scripts/` as hand-written, numbered files: SQL files from `migrate_0001a_…sql` onwards, followed by Python data migrations (`migrate_0020_hero_to_catalogue.py`, `migrate_0021_freeze_is_history.py`) that dry-run by default and commit only with `--apply`. A person applies them by hand. `CODE-REVIEW-BRIEF.md` lists this as a deliberate omission — *"No Alembic; hand-written SQL + `create_all`"* — on the grounds that migrations are meant to be *read*, and numbered files beat a generated chain.

**Nothing records which of those files a database has had.** `backend/main.py` runs `Base.metadata.create_all(bind=engine)` at startup, which creates missing tables and never alters existing ones. A database that has missed a migration starts cleanly and fails later.

**That is what happened on 2026-09-20.** `migrate_0019` renamed three `snapshots` columns; the models and tests moved with it; the dev database was not migrated. Every query touching `snapshots` raised, including the one the dashboard runs on sign-in, so signing in returned a 500 whose cause sat four layers from the symptom.

**The test suite cannot catch this by construction, and that is correct rather than a gap to close here.** The session fixture in `backend/tests/conftest.py` drops and recreates the schema from the models on every run and refuses to connect to the dev database. Its docstring gives the reason: the migrations are *"historical deltas that assume a populated database (0012 literally encodes a row count measured on the dev database), and the models are the schema of record."* A green suite therefore says the code matches the models; it says nothing about whether a given database does.

**`backend/scripts/check_schema.py`, written after the incident, only half-answers the question.** It diffs model columns against a live database and exits non-zero on a difference. Its docstring calls it *"a detector, not a runner, because a script that silently ALTERs a database holding real work is a worse failure than the one it prevents"* — a principle this record keeps. But nothing runs it, and more importantly **a column comparison cannot see a data migration.** 0020 and 0021 change rows, not columns: a database that never had 0020 passes `check_schema` and still has hero modules carrying copy the renderer no longer reads.

**Three options were put to the user.**

- **Run the schema comparison at startup.** This would have stopped the 2026-09-20 failure, but it leaves data migrations invisible and still cannot say which files a database has had — only whether its columns happen to match today.
- **A ledger table plus an explicit runner.** Chosen, and set out below.
- **Adopt Alembic.** This reverses the brief's reasoning outright and replaces readable, hand-written files with a generated chain, which is the thing the brief argued against.

**The chosen option refines the brief rather than reversing it.** The brief argued against a *generated chain*, not against knowing a database's state. The files stay hand-written, numbered and meant to be read; what changes is that a database now remembers which of them it has had.

The precedent for refusing at boot is [[ADR-162 — Channel Rendering and Artifacts]] point 5: `backend/main.py` calls `assert_manifests_load()`, which stops the process on a misfiled module manifest rather than letting it surface on a manager's request. A database missing a migration is the same class of fault — known at startup, currently discovered on a request.

## Decision

**1. A `schema_migrations` table holds one row per migration file.**
Each row carries the filename, when it was recorded, and `how` it came to be recorded, which is one of three values:

- `ran` — the runner applied the file.
- `baseline` — a person asserted, after checking, that the database already reflects the file. It was not run.
- `built` — the schema was built from the models, so it is at head by construction.

**These are kept distinct because they are different claims.** Only `ran` is evidence that the file executed; the other two are, respectively, a checked assertion and a consequence of how the database was made. Collapsing them would let the ledger claim more than it knows.

**2. A migration is a file in `backend/scripts/` named `migrate_*.sql` or `migrate_*.py`, ordered by filename.**
They remain hand-written, numbered and meant to be read. Nothing is generated.

**3. The application refuses to start while any migration file has no row.**
The refusal names the unrecorded files and the command that applies them, following [[ADR-162 — Channel Rendering and Artifacts]] point 5's startup assertion. **Refuse, not warn:** a log warning is how the incident would have gone unnoticed anyway. On 2026-09-20 the application started cleanly and failed on the first request that mattered; a warning at boot would have been one more line nobody read before that request.

**4. Nothing applies a migration except a person running `backend/scripts/migrate.py`.**
By default it reports status. With `--apply` it runs pending files in filename order, each atomically, records each one as `ran` on success, and stops at the first failure. **Startup never applies anything** — the principle `check_schema.py` already states: silently altering a database that holds real work is a worse failure than the one it prevents.

**5. A schema built from nothing by `create_all` records every migration file as `built`.**
The test database is always such a database — dropped and rebuilt on every run — and records itself so before the application is imported, so the startup refusal in point 3 does not fire under test.

**6. An existing database with no rows is refused until it is baselined.**
`migrate.py --baseline` records every unrecorded file as `baseline`, **and only after `check_schema.py` reports no difference**, so a database that is out of date cannot be declared current. A baseline cannot check data, and it says so when it runs; the `baseline` value in the row records that it was an assertion rather than evidence.

**7. A ledger row for a file no longer on disk is reported, not refused.**
Refusing would be a refusal nobody could satisfy, since the missing file cannot be applied.

## Consequences

### Positive

- **The 2026-09-20 failure becomes a boot-time refusal that names the file.** A database that has missed `migrate_0019` stops at startup with the filename and the command, instead of returning a 500 on sign-in whose cause is four layers away.
- **Data migrations are covered.** A database that never had 0020 is refused the same way as one that never had a column rename, which no column comparison could achieve.
- **The brief's readability argument survives intact.** The files are still hand-written and numbered; the ledger records that they ran, not what they are.
- **It makes task-12 tractable.** Building a database by applying every migration to an empty one and diffing it against `create_all` needs a runner that applies files in order and stops on failure; that runner now exists.
- **The ledger is honest about its own evidence.** `how` distinguishes a file that executed from one that was asserted or built past, so nobody reading the table later mistakes a baseline for a run.

### Negative

- **Every existing database, including dev, needs a one-time baseline before the application will start.** Until someone runs `migrate.py --baseline`, the application refuses — by design, but it is a step that did not exist before.
- **The ledger records filenames, not contents.** There is no checksum, so an edit to an already-applied migration is invisible to it. This is deliberate: editing an applied file to fix a comment is ordinary here, and a checksum would turn that into a refusal.
- **A baseline is an assertion for data.** `check_schema.py` can confirm the columns before a baseline is recorded; nothing confirms that 0020 or 0021's row changes are present. The `baseline` value records that gap rather than closing it.
- **The test database records itself current rather than proving it.** Marking every file `built` is true by construction, but it does not show that the migrations, applied in order, produce the models' schema. That is still task-12's question.
- **Old migrations were not written for a runner.** Several assume a populated database — 0012 encodes a row count measured on the dev database — so `--apply` against an empty database is unsupported. Fresh databases come from the models, not from replaying the history.

## Notes

- **This is not a supersession and no ADR's status changes.** No ADR recorded the brief's "no Alembic" choice, and this record refines that choice rather than reversing it. The repository's one supersession remains [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001.
- **`CODE-REVIEW-BRIEF.md`'s "No Alembic" row will be updated to name this record**, so the deliberate omission and the ledger that now sits beside it are read together.
- **`docs/playbook-strategy.md` carries no decision-log entry for this decision** (checked 2026-09-29). It was argued and decided in task-1, which is the record of the reasoning.
- **`check_schema.py` keeps its role and gains a caller.** It is still a detector, not a runner; point 6 makes it the gate a baseline must pass, which answers the "nothing runs it" gap for the one moment it matters most.

## Related ADRs

### Depends On
- [[ADR-162 — Channel Rendering and Artifacts]]
