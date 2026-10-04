"""The migration ledger — ADR-181.

A database records which migrations it has had, and the application refuses to
start while one is pending. These tests run the ledger against a temporary
directory of throwaway migration files, so they say what the ledger does
without depending on which real migrations exist this week.

**Every test starts from an empty ledger** and the real rows are put back
afterwards. conftest records the test database as `built` for every real file;
leaving those rows in would make "a database with no ledger" impossible to
construct and every temporary file's neighbours look like orphans.
"""
import logging
import uuid

import pytest
from sqlalchemy import inspect, text

from app import schema_migrations as ledger
from app.database import Base, SessionLocal, engine


@pytest.fixture
def db():
    session = SessionLocal()
    saved = [(r.filename, r.how) for r in session.query(ledger.SchemaMigrationDB).all()]
    session.query(ledger.SchemaMigrationDB).delete()
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.query(ledger.SchemaMigrationDB).delete()
        for filename, how in saved:
            session.add(ledger.SchemaMigrationDB(filename=filename, how=how))
        session.commit()
        session.close()


@pytest.fixture
def migrations(tmp_path):
    """A directory shaped like `backend/scripts/`, with one file of each kind
    and some neighbours that must NOT count as migrations."""
    directory = tmp_path / "scripts"
    directory.mkdir()
    (directory / "migrate_0001a_first.sql").write_text("SELECT 1;")
    (directory / "migrate_0001b_second.sql").write_text("SELECT 1;")
    (directory / "migrate_0002_third.py").write_text("print('ok')\n")
    (directory / "check_schema.py").write_text("")
    (directory / "seed_demo_data.py").write_text("")
    (directory / "migrate_notes.md").write_text("")
    return directory


class TestWhatCountsAsAMigration:

    def test_files_are_ordered_by_name_and_neighbours_are_ignored(self, migrations):
        assert ledger.migration_files(migrations) == [
            "migrate_0001a_first.sql",
            "migrate_0001b_second.sql",
            "migrate_0002_third.py",
        ]


class TestTheStartupCheck:
    """ADR-181 points 3, 5, 6 and 7."""

    def test_a_database_built_from_nothing_is_recorded_as_built(self, db, migrations):
        ledger.assert_no_pending_migrations(db, built_from_nothing=True, directory=migrations)

        assert ledger.recorded(db) == {
            name: ledger.BUILT for name in ledger.migration_files(migrations)
        }

    def test_a_pending_file_stops_startup_and_is_named(self, db, migrations):
        """The 2026-09-20 incident, as a refusal instead of a 500 on sign-in."""
        ledger.record(db, ["migrate_0001a_first.sql", "migrate_0001b_second.sql"], ledger.RAN)

        with pytest.raises(ledger.PendingMigrations) as refusal:
            ledger.assert_no_pending_migrations(db, built_from_nothing=False, directory=migrations)

        assert "migrate_0002_third.py" in str(refusal.value)
        assert "migrate.py --apply" in str(refusal.value), (
            "the refusal did not say how to fix it, so the person reading it at "
            "boot has to go and find out"
        )

    def test_a_database_with_no_ledger_is_told_to_baseline(self, db, migrations):
        """An existing database whose history is unknown. Every file looks
        pending, and telling the person to --apply would re-run migrations
        that were never written to run twice."""
        with pytest.raises(ledger.PendingMigrations) as refusal:
            ledger.assert_no_pending_migrations(db, built_from_nothing=False, directory=migrations)

        assert "--baseline" in str(refusal.value)
        assert "--apply" not in str(refusal.value)

    def test_a_current_database_starts(self, db, migrations):
        ledger.record(db, ledger.migration_files(migrations), ledger.RAN)

        ledger.assert_no_pending_migrations(db, built_from_nothing=False, directory=migrations)

    def test_a_recorded_file_no_longer_on_disk_warns_and_does_not_refuse(
        self, db, migrations, caplog
    ):
        ledger.record(db, ledger.migration_files(migrations) + ["migrate_0000_gone.sql"], ledger.RAN)

        with caplog.at_level(logging.WARNING, logger="app.schema_migrations"):
            ledger.assert_no_pending_migrations(db, built_from_nothing=False, directory=migrations)

        assert "migrate_0000_gone.sql" in caplog.text


class TestTheLedgerKeepsItsEvidence:

    def test_a_later_claim_never_overwrites_an_earlier_one(self, db, migrations):
        """`ran` is the only evidence a file executed. A baseline recorded over
        it would replace evidence with an assertion."""
        ledger.record(db, ["migrate_0001a_first.sql"], ledger.RAN)

        ledger.record(db, ["migrate_0001a_first.sql"], ledger.BASELINE)

        assert ledger.recorded(db)["migrate_0001a_first.sql"] == ledger.RAN


class TestBaseline:
    """ADR-181 point 6."""

    def test_a_baseline_is_refused_while_the_schema_disagrees(self, db, migrations):
        with pytest.raises(RuntimeError, match="Refusing to baseline"):
            ledger.baseline(db, schema_matches=False, directory=migrations)

        assert ledger.recorded(db) == {}, "a refused baseline still recorded something"

    def test_a_baseline_records_every_unrecorded_file_as_baseline(self, db, migrations):
        ledger.record(db, ["migrate_0001a_first.sql"], ledger.RAN)

        ledger.baseline(db, schema_matches=True, directory=migrations)

        assert ledger.recorded(db) == {
            "migrate_0001a_first.sql": ledger.RAN,
            "migrate_0001b_second.sql": ledger.BASELINE,
            "migrate_0002_third.py": ledger.BASELINE,
        }


class TestApply:
    """ADR-181 point 4: in order, each recorded as it succeeds, stop at the
    first failure."""

    @pytest.fixture
    def probe_table(self):
        name = f"ledger_probe_{uuid.uuid4().hex[:8]}"
        yield name
        with engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {name}"))

    def test_pending_files_run_in_order_and_are_recorded_as_ran(
        self, db, migrations, probe_table
    ):
        (migrations / "migrate_0001a_first.sql").write_text(
            f"CREATE TABLE {probe_table} (id int);"
        )
        (migrations / "migrate_0001b_second.sql").write_text(
            f"INSERT INTO {probe_table} VALUES (1);"
        )
        marker = migrations.parent / "python_migration_ran"
        (migrations / "migrate_0002_third.py").write_text(
            "import sys, pathlib\n"
            "assert '--apply' in sys.argv, 'run without --apply'\n"
            f"pathlib.Path({str(marker)!r}).write_text('yes')\n"
        )

        ran = ledger.apply_pending(db, engine, directory=migrations)

        assert ran == ledger.migration_files(migrations)
        assert set(ledger.recorded(db).values()) == {ledger.RAN}
        with engine.connect() as connection:
            # The INSERT only succeeds if the CREATE ran first: order, proven
            # by the data rather than by reading the return value.
            assert connection.execute(text(f"SELECT count(*) FROM {probe_table}")).scalar() == 1
        assert marker.exists(), "the Python migration was not run with --apply"

    def test_a_failing_file_stops_the_run_and_is_not_recorded(
        self, db, migrations, probe_table
    ):
        (migrations / "migrate_0001a_first.sql").write_text("SELECT 1;")
        (migrations / "migrate_0001b_second.sql").write_text(
            f"CREATE TABLE {probe_table} (id int); SELECT * FROM no_such_table;"
        )

        with pytest.raises(Exception):
            ledger.apply_pending(db, engine, directory=migrations)
        db.rollback()

        assert ledger.recorded(db) == {"migrate_0001a_first.sql": ledger.RAN}, (
            "a failed file was recorded, or the run carried on past it"
        )
        assert probe_table not in inspect(engine).get_table_names(), (
            "the failing file's first statement survived — a file must be "
            "atomic, or a half-applied migration is recorded as not applied"
        )

    def test_a_failing_python_migration_stops_the_run(self, db, migrations):
        (migrations / "migrate_0002_third.py").write_text("raise SystemExit(3)\n")

        with pytest.raises(RuntimeError, match="exited 3"):
            ledger.apply_pending(db, engine, directory=migrations)

        assert "migrate_0002_third.py" not in ledger.recorded(db)


class TestModelRegistration:

    def test_walking_db_models_registers_every_table_main_does(self):
        """`check_schema` and the runner register models by walking the
        `db_models` modules, because importing `main` now runs the startup
        check — which refuses on exactly the database a baseline is for. The
        walk is only safe if it misses nothing `main` knows about. A model
        defined outside a `db_models` module would fail here."""
        import main  # noqa: F401 — already imported by the suite; this names the dependency

        through_main = set(Base.metadata.tables)
        ledger.import_all_models()

        assert set(Base.metadata.tables) == through_main
        # And the walk alone must reach every one of them. A fresh interpreter
        # is the only honest way to ask, since this process imported main.
        import subprocess
        import sys
        from pathlib import Path

        backend = Path(__file__).resolve().parents[1]
        walked = subprocess.run(
            [sys.executable, "-c",
             "from app.schema_migrations import import_all_models; "
             "from app.database import Base; import_all_models(); "
             "print('\\n'.join(sorted(Base.metadata.tables)))"],
            cwd=str(backend), capture_output=True, text=True, check=True,
        ).stdout.split()
        assert set(walked) == through_main, (
            f"missed by the walk: {sorted(through_main - set(walked))}"
        )


class TestStartupActuallyRefuses:
    """The call site, not the function.

    Every test above calls `assert_no_pending_migrations` directly, so they
    would all pass if `main.py` stopped calling it — the shape that has let a
    test go green while guarding nothing four times already in this codebase.
    This one imports `main` in a fresh process against a test database with one
    real migration unrecorded, and expects the process to refuse.
    """

    def test_importing_main_with_a_pending_migration_exits_and_names_it(self):
        import os
        import subprocess
        import sys
        from pathlib import Path

        from tests.conftest import TEST_DATABASE_URL

        url = os.environ["DATABASE_URL"]
        assert url == TEST_DATABASE_URL, (
            f"refusing to run a startup probe against {url!r}: not the test database"
        )

        newest = ledger.migration_files()[-1]
        with SessionLocal() as session:
            row = session.get(ledger.SchemaMigrationDB, newest)
            assert row is not None, "conftest should have recorded every real file"
            how = row.how
            session.delete(row)
            session.commit()
        try:
            backend = Path(__file__).resolve().parents[1]
            probe = subprocess.run(
                [sys.executable, "-c", "import main"],
                cwd=str(backend), capture_output=True, text=True, timeout=60,
            )
        finally:
            with SessionLocal() as session:
                if session.get(ledger.SchemaMigrationDB, newest) is None:
                    session.add(ledger.SchemaMigrationDB(filename=newest, how=how))
                    session.commit()

        assert probe.returncode != 0, (
            "main started against a database with a pending migration — "
            "the startup check is not being called"
        )
        assert "PendingMigrations" in probe.stderr
        assert newest in probe.stderr, "the refusal did not name the pending file"
