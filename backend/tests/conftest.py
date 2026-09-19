"""Point the suite at a database of its own — and refuse to run without one.

**This file exists for one reason that nothing else could solve: import order.**
`app/database.py` builds its engine at module import, from a `DATABASE_URL`
whose default is the shared dev database. Every test module imports `app.*`
near the top, before `main`, so by the time any other code could redirect the
connection it is already bound. A `.env` entry cannot do it either — `main.py`
loads `.env` *after* the first `app.database` import a test has already
triggered. `conftest.py` is imported by pytest before any test module, which
makes it the only place the redirect can happen at all.

**Why a second Postgres database and not SQLite.** It was considered and it is
not viable, for a reason worth writing down so nobody re-proposes it as a
speed-up: `ux_content_overrides_one_active_per_module` is a PARTIAL unique
index (`WHERE active`). SQLite silently drops the `postgresql_where` clause and
builds a full unique index, so resetting an override would start raising
`IntegrityError` — behaviour changing quietly rather than loudly, which is the
worst failure a test harness can have. `with_for_update()` is likewise ignored
there, so four concurrency guards would pass vacuously, and `func.now()`
renders a naive second-resolution string against columns declared
`DateTime(timezone=True)`, which the signal-decay maths reads directly.

**Why not a truncate-and-reseed of the dev database**, which is the obvious
cheap answer and was rejected on 2026-07-31: the dev database holds real work —
imported content, live campaigns, accumulated engagement signals — so a suite
that truncates it is worse than the problem it solves.
"""

import os
from urllib.parse import urlsplit, urlunsplit

import pytest

#: The dev database, which this suite must never touch.
DEV_DEFAULT = (
    "postgresql://newsletter_user:newsletter_password@localhost:5432/newsletter"
)


def _test_database_url() -> str:
    """Where the suite runs. `TEST_DATABASE_URL` wins; otherwise `<dev>_test`.

    Derived from the dev URL rather than hardcoded so that a developer who
    moved their Postgres — a different port, a different password — gets a test
    database beside it without configuring anything twice.
    """
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    parts = urlsplit(os.environ.get("DATABASE_URL") or DEV_DEFAULT)
    return urlunsplit(parts._replace(path=parts.path.rstrip("/") + "_test"))


def _database_name(url: str) -> str:
    return urlsplit(url).path.lstrip("/")


def _refuse_the_dev_database(url: str) -> None:
    """A suite that can truncate real work is worse than the problem it fixes.

    Checked on the name rather than the whole URL, because the two differ only
    there and a host or password typo must not be what saves us.
    """
    name = _database_name(url)
    if not name:
        raise RuntimeError(f"no database named in {url!r}")
    if name == _database_name(DEV_DEFAULT) or name == _database_name(
        os.environ.get("DATABASE_URL") or ""
    ):
        raise RuntimeError(
            f"refusing to run the test suite against {name!r}, which is the "
            "development database. The suite truncates and reseeds; set "
            "TEST_DATABASE_URL to something disposable."
        )


def _ensure_database_exists(url: str) -> None:
    """Create it on first use, so a fresh checkout needs no setup step.

    Connects to the `postgres` maintenance database, because you cannot create
    a database from inside itself.
    """
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    parts = urlsplit(url)
    name = _database_name(url)
    admin = urlunsplit(parts._replace(path="/postgres"))
    connection = psycopg2.connect(admin)
    try:
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            if cursor.fetchone() is None:
                # Identifier interpolation, because a database name cannot be a
                # bound parameter. The value comes from this process's own
                # environment, not from a request.
                cursor.execute(f'CREATE DATABASE "{name}"')
                print(f"\n[conftest] created the test database {name!r}")
    finally:
        connection.close()


# --- and this must happen before anything imports app.database --------------
TEST_DATABASE_URL = _test_database_url()
_refuse_the_dev_database(TEST_DATABASE_URL)
_ensure_database_exists(TEST_DATABASE_URL)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def _known_state():
    """Build the schema and put a known dataset in it, once per run.

    **Known state is the point, not merely isolation.** The 2026-07-31 entry
    that asked for this database diagnosed the real damage precisely: tests had
    been rewritten to tolerate drift — resolving fixtures by shape, asserting
    on deltas rather than absolutes — because the data underneath them moved.
    That treated the symptom. With a database the suite owns, roughly forty
    tests can reach for a variant or a sent send instance again and find one,
    and assertions can go back to being absolute.

    `create_all` rather than the migrations: those are historical deltas that
    assume a populated database (0012 literally encodes a row count measured on
    the dev database), and the models are the schema of record.
    """
    from app.database import Base, engine
    from app.auth import service as auth
    from app.database import SessionLocal

    assert str(engine.url).endswith("_test") or os.environ.get("TEST_DATABASE_URL"), (
        f"the engine bound to {engine.url!r}, which is not the test database — "
        "something imported app.database before this conftest ran"
    )

    # Every model module, imported for its side effect of registering tables on
    # `Base.metadata`. `create_all` builds only what it has been told about, so
    # a model nobody imported is a table that silently does not exist.
    import main  # noqa: F401  — imports every router, and therefore every model

    # **Dropped and rebuilt, not created-if-missing.** `create_all` skips a
    # table that already exists, INCLUDING its indexes — so a constraint added
    # to a model later never reaches a test database built before it, and the
    # harness quietly enforces a different schema from production. That
    # happened within an hour of this file existing: `pending_actions` lost its
    # partial unique index and two tests started passing against a database
    # that could not have refused them.
    #
    # Disposable has to mean disposable. The models are the schema of record,
    # and this is the only way to be sure the suite is running against them.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        auth.bootstrap(session)
    finally:
        session.close()

    from scripts import seed_demo_data

    seed_demo_data.seed()
    _ensure_send_instances_in_both_states()
    yield


def _ensure_send_instances_in_both_states() -> None:
    """The two rows the demo seed does not leave behind.

    Tests need a `sent` send instance (to assert that sending it again is
    refused) and a `draft` one (to assert that sending works at all). The seed
    fires its single send through the mock provider, which lands it in whatever
    state the audience produced — `no_recipients` for an empty one — so neither
    state is guaranteed.

    Marked here rather than in the seed, because the seed describes a plausible
    company and this describes what the harness needs. A seed that claimed to
    have sent something it did not send would be a lie in the demo data, and
    the demo data is also what a person looks at.
    """
    from app.database import SessionLocal
    from app.delivery.db_models import SendInstanceDB

    session = SessionLocal()
    try:
        rows = session.query(SendInstanceDB).order_by(SendInstanceDB.id).all()
        if not rows:
            return
        states = {row.status for row in rows}

        if "sent" not in states:
            rows[0].status = "sent"

        if "draft" not in states:
            # Through the ORM, not raw SQL: `sent_count` and friends carry
            # PYTHON-side defaults, which an INSERT statement never sees. The
            # first version of this used `text()` and hit a not-null violation
            # on a column the model fills for free.
            source = rows[0]
            session.add(SendInstanceDB(
                snapshot_id=source.snapshot_id,
                brand_id=source.brand_id,
                name=f"{source.name} (draft, for the test suite)",
                status="draft",
                provider=source.provider,
            ))
        session.commit()
    finally:
        session.close()
