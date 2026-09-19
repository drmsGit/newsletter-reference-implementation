---
type: code-note
topic:
  - testing
  - development
created: 2026-09-19
---

# The test database, and the rule it exists to enforce

**Not an ADR, deliberately.** How the suite gets a database is tooling, the same
call made for the reference deployment: infrastructure rather than architecture.
But the rule it establishes shapes every test written from here on, so it is
written down rather than left in a commit message.

> **A test owns its data. The test database is disposable, and the development
> database is never touched.**

## What happens when you run `pytest`

`backend/tests/conftest.py` redirects the suite to a second Postgres database —
`newsletter_test` by default, beside your development one on the same instance —
creating it on first use. Then, once per run, it drops and rebuilds the schema
from the models and seeds a known dataset.

Nothing to configure. `TEST_DATABASE_URL` overrides the destination if you want
it elsewhere.

## Four decisions worth keeping

**It lives in `conftest.py` because nothing else can reach early enough.**
`app/database.py` builds its engine at module import, from a `DATABASE_URL`
whose default is the development database. Every test module imports `app.*`
before `main`, so by the time anything else could redirect the connection it is
already bound — and a `.env` entry cannot do it either, because `main.py` loads
`.env` after the first `app.database` import a test has already triggered.
pytest imports `conftest.py` before any test module. That is the only window.

**It refuses to run against the development database.** Checked on the database
name, and it raises rather than warning. A suite that truncates and reseeds must
not be one typo away from deleting real work — imported content, live campaigns,
accumulated engagement signals.

**Not SQLite, and this is the part most likely to be re-proposed as a speed-up.**
`ux_content_overrides_one_active_per_module` is a *partial* unique index
(`WHERE active`). SQLite silently drops the `postgresql_where` clause and builds
a full unique index, so resetting an override would start raising
`IntegrityError` — behaviour changing quietly rather than loudly, which is the
worst failure a harness can have. Beyond that, `with_for_update()` is ignored at
four sites, so every concurrency guard would pass vacuously, and `func.now()`
renders a naive second-resolution string into columns declared
`DateTime(timezone=True)`, which the signal-decay maths reads directly.

**The schema is dropped and rebuilt, not created-if-missing.** `create_all`
skips a table that already exists, *including its indexes*, so a constraint
added to a model later never reaches a test database built before it. That
happened within an hour of this file existing: `pending_actions` lost its partial
unique index and two tests began passing against a database that could not have
refused them. Disposable has to mean disposable.

## Known state, not merely isolation

The suite seeds `auth.bootstrap()` plus `scripts/seed_demo_data.py`, so about
forty tests can reach for a variant, a decision slot or a sent send instance and
find one.

That is the point rather than a convenience. Tests had been rewritten to
tolerate drift — resolving fixtures by shape, asserting on deltas instead of
absolutes — because the data underneath them moved. With a database the suite
owns, assertions can be absolute again.

**So absence is now a failure, not a skip.** `tests/test_overrides.py` used to
call `pytest.skip(allow_module_level=True)` at import when it found no suitable
module instance, which meant an emptied database made all thirteen of its tests
disappear during collection — a green run proving nothing. It raises now. If the
seed changes shape, fix the seed.

## What this immediately found

Running the seed against an empty database, which had never been done, surfaced
two ways it had rotted against the schema:

- `consent_events` were inserted with no `brand_id`, which became `NOT NULL`
  when consent went per-brand;
- variants were created with `subject=` and `preheader=` keyword arguments,
  columns that migration 0012 dropped when ADR-162 made them module fields.

Neither was visible while the seed only ever ran against a database that already
had rows in it.

## Writing tests from here

- Create what you assert on. Reaching for "the first variant" is how a suite
  becomes coupled to whatever happened to be there.
- Clean up in `finally`, and **roll back first** — Postgres refuses every command
  on an aborted transaction, so a teardown sharing a connection with the failure
  cannot run until it clears the failure.
- Audit rows carry no foreign keys and do not cascade. A fixture that deletes a
  subject must delete its audit entries explicitly.
- Remember that a **mutation test commits**. Breaking a guard does not merely
  fail a test, it performs the thing the guard prevented — which has left leaked
  rows, wrongly-expired demo requests and a changed settings row. An isolated
  database is what makes that harmless.

## Related

- `docs/backlog.md` — the 2026-07-31 entry that asked for this
- `backend/tests/conftest.py` — the implementation, with the reasoning inline
