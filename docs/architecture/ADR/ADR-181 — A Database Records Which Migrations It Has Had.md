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

## Addendum 2026-09-29 — the schema check compares everything, and runs after every apply

Prompted by task-12, decided by the user on 2026-09-29. Points 1 to 7 stand as
written. This addendum records what task-12 found and what the check became.

**task-12's literal question cannot be asked.** It asked for a database built
both ways and diffed. The migrations in `backend/scripts/` are deltas over a
schema that `create_all` built around 2026-09-12 and that no file records.
0001a backfills from columns it replaces. So the migrations cannot build a
database from empty, and the migrations path exists only as real databases.
This is the negative consequence above about old migrations, made concrete.
`pg_dump` and `psql` are not installed, so the check introspects through
SQLAlchemy.

**The column-name check had passed a database that differed in 14 ways.** A
full, name-independent comparison of the development database against a fresh
`create_all` build found:

- **Eight server-side defaults the models do not declare.** Migrations added
  NOT NULL columns with `DEFAULT x` to backfill them, while the models use
  Python-side `default=`. Five are harmless:
  `send_instances.sent_count`, `failed_count` and `excluded_count` (0),
  `consent_sync_logs.changes_applied` (0) and `.ok` (true), and
  `roles.is_customised` (false).
- **Three of those defaults fail open, which the ADRs refuse.**
  `send_instances.audience_resolution_mode DEFAULT 'freeze'` contradicts the
  model's `'rerun'` since [[ADR-176 — A Negative Decision Outranks a Positive One]]
  point 4 was implemented that morning. A raw insert that omits the column gets
  the mode ADR-176 removed. `delivery_executions.channel DEFAULT 'email'` is the
  channel-default class that ADR-176's 2026-09-27 addendum removed from
  `resolve_audience`. `delivery_executions.purpose DEFAULT 'marketing'` is the
  same kind of guess.
- **Three indexes on `pending_actions`** created by migration 0017 and never
  declared in the models, so test databases lacked them.
- **One piece of debris.** Both paths make
  `delivery_executions.provider_message_id` unique: the migrated database by a
  UNIQUE constraint, the models by a unique index. The migrated database also
  carries a redundant plain index. That is debris, not disagreement.

`backend/scripts/check_schema.py` compared column names only, so it saw none of
the 14. Point 6's baseline gate had passed the development database on that
weaker check.

**1. The check is a full comparison against a database built from the models.**
`check_schema` builds a scratch database with `create_all` and compares tables,
columns (type, nullability, default), indexes and constraints. It compares them
name-independently, so a UNIQUE constraint and a unique index are the same rule.
Then it drops the scratch database. This is the stricter reading of the
`check_schema.py` that point 6 already requires before a baseline, not a new
gate.

**2. A difference is either behind or debris, and only one fails.** Anything
the models declare that the database lacks or holds differently, including a
default, is *behind or disagreeing*, and fails. An index or column that exists
only in the database is *debris*, and is reported, not failed. This follows
`check_schema.py`'s existing rule that "deliberate should be a decision somebody
remembers making".

**3. The runner verifies after applying.** `migrate.py --apply` runs the
comparison once the pending files have run. That is the moment a migration
either reaches the models' schema or does not. It answers task-12 going forward
without a stored snapshot.

**4. The database never supplies a default the models do not declare.** This is
a new rule. Migration `migrate_0024` drops the three fail-open defaults. The five
harmless ones are declared as `server_default` in the models, so the two paths
agree. The three `pending_actions` indexes are declared in the models too.

A frozen baseline schema file, replayed with new migrations in CI, was
considered and not adopted. It would be a large generated file, and only as
trustworthy as the database it was generated from. Checking the real database
after every `--apply` tests exactly the thing that drifts.

**What it costs.**

- **The check needs permission to create a database.** A role without it gets a
  clear "cannot compare", never a pass.
- **The Python-side defaults stay.** `DeliveryExecutionDB` still carries
  `default="email"` and `default="marketing"`. They are the same fail-open
  class, but they are scoped to task-42 and not changed here. Only the
  database-side copies are removed.
- **The development database reports its redundant `provider_message_id` index
  as debris on every run** until someone decides to drop it.

The negative consequence above that the test database "does not show that the
migrations, applied in order, produce the models' schema" still holds for an
empty database. What changes is that every real database is now checked against
the models each time a migration is applied to it.

## Related ADRs

### Depends On
- [[ADR-162 — Channel Rendering and Artifacts]]
