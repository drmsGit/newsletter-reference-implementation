"""The full schema comparison — task-12, ADR-181 addendum of 2026-09-29.

`check_schema` used to compare column NAMES, and the development database
passed it while carrying fourteen differences. It now compares a live database
with a scratch one built from the models: columns with type, nullability and
default; indexes; constraints — all with names removed, because the two paths
name things differently and a name is not a rule.

The test database is itself built from the models, so comparing it with a
fresh models build must find NOTHING. That is the test that matters most: a
check that reports differences between two identical schemas would be ignored
within a week, and one that normalises too much would pass anything.
"""
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import schema_compare
from app.database import engine

BACKEND = Path(__file__).resolve().parents[1]


def _col(typ, nullable=False, default=None):
    return (typ, nullable, default)


def _table(columns=None, indexes=(), constraints=()):
    return {"columns": columns or {}, "indexes": set(indexes), "constraints": set(constraints)}


class TestTheComparisonAgainstItself:

    def test_a_database_built_from_the_models_matches_a_fresh_models_build(self):
        result = schema_compare.check(engine)

        assert result.failures == [], "\n".join(result.failures)
        assert result.debris == [], "\n".join(result.debris)

    def test_the_scratch_database_is_dropped_afterwards(self):
        schema_compare.check(engine)

        url = make_url(engine.url.render_as_string(hide_password=False))
        with engine.connect() as c:
            left = c.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": f"{url.database}_schemacheck"},
            ).first()
        assert left is None, "the scratch database was left behind"


class TestWhatFailsAndWhatIsDebris:
    """ADR-181 addendum point 2. Behind or disagreeing fails; only-in-the-
    database is reported and does not."""

    def test_a_default_the_models_do_not_declare_is_a_failure(self):
        """The class that hid `audience_resolution_mode DEFAULT 'freeze'`."""
        live = {"t": _table({"mode": _col("varchar(20)", default="'freeze'::character varying")})}
        models = {"t": _table({"mode": _col("varchar(20)")})}

        result = schema_compare.compare(live, models)

        assert not result.agrees
        assert "DEFAULT 'freeze'" in result.failures[0]

    def test_an_index_the_models_declare_and_the_database_lacks_is_a_failure(self):
        live = {"t": _table()}
        models = {"t": _table(indexes={"CREATE INDEX USING btree (a)"})}

        assert not schema_compare.compare(live, models).agrees

    def test_an_index_only_the_database_has_is_debris(self):
        """`provider_message_id`'s redundant index on the dev database."""
        live = {"t": _table(indexes={"CREATE INDEX USING btree (a)"})}
        models = {"t": _table()}

        result = schema_compare.compare(live, models)

        assert result.agrees
        assert len(result.debris) == 1

    def test_a_missing_table_or_column_is_a_failure(self):
        models = {"t": _table({"a": _col("int4")}), "u": _table()}
        live = {"t": _table()}

        failures = schema_compare.compare(live, models).failures

        assert any("t.a" in f for f in failures)
        assert any("table u" in f for f in failures)

    def test_a_constraint_only_the_database_enforces_is_a_failure_not_debris(self):
        """Unlike an index, an extra constraint changes what the database will
        refuse — so a test database without it passes writes production
        rejects. That is the pending_actions incident's shape."""
        live = {"t": _table(constraints={("c", "CHECK ((a > 0))")})}
        models = {"t": _table()}

        assert not schema_compare.compare(live, models).agrees


class TestTheDefaultsRule:
    """The database never supplies a default the models do not declare.
    Three defaults were dropped rather than declared, because each chose a
    value nobody chose; this pins that the models do not bring them back."""

    def test_the_fail_open_defaults_are_not_declared(self):
        declared = schema_compare.describe(engine)
        for table, column in (
            ("send_instances", "audience_resolution_mode"),
            ("delivery_executions", "channel"),
            ("delivery_executions", "purpose"),
        ):
            _, _, default = declared[table]["columns"][column]
            assert default is None, (
                f"{table}.{column} has a database default again ({default}) — "
                "migration 0024 dropped it because a value nobody chose is a "
                "fail-open default"
            )


class TestTheRunnerVerifiesAfterApplying:
    """The call site. `migrate.py --apply` must run the comparison, or a
    migration that misses the models is found on a request instead."""

    def test_apply_reports_the_schema_check(self):
        probe = subprocess.run(
            [sys.executable, "scripts/migrate.py", "--apply"],
            cwd=str(BACKEND), capture_output=True, text=True, timeout=120,
            env={**os.environ},
        )

        assert "schema check:" in probe.stdout, probe.stdout + probe.stderr
        assert probe.returncode == 0, probe.stdout + probe.stderr


class TestTwoPathsThatSayTheSameThing:
    """What the self-comparison cannot prove.

    Two builds from the same models share every name, so comparing them says
    nothing about the normalisation — the part that lets a migrated database and
    a models-built one be compared at all. The migrations write
    `UNIQUE (provider_message_id)` as a constraint; a model's
    `unique=True, index=True` writes a unique index under a different name.
    Both refuse the duplicate, and the check must say so.
    """

    def _scratch(self, suffix, ddl):
        from sqlalchemy import create_engine

        url = make_url(engine.url.render_as_string(hide_password=False))
        name = f"{url.database}_cmp{suffix}"
        admin = create_engine(url, isolation_level="AUTOCOMMIT")
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            c.execute(text(f'CREATE DATABASE "{name}"'))
        built = create_engine(url.set(database=name))
        with built.begin() as c:
            for statement in ddl:
                c.execute(text(statement))
        return admin, built, name

    def _drop(self, admin, built, name):
        built.dispose()
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()

    def test_a_unique_constraint_and_a_differently_named_unique_index_agree(self):
        a = self._scratch("a", [
            "CREATE TABLE t (id serial PRIMARY KEY, m varchar(255))",
            "ALTER TABLE t ADD CONSTRAINT t_m_key UNIQUE (m)",
            "CREATE INDEX ix_t_a_n ON t (id, m)",
        ])
        b = self._scratch("b", [
            "CREATE TABLE t (id serial PRIMARY KEY, m varchar(255))",
            "CREATE UNIQUE INDEX ix_t_m ON t (m)",
            "CREATE INDEX some_other_name ON t (id, m)",
        ])
        try:
            result = schema_compare.compare(
                schema_compare.describe(a[1]), schema_compare.describe(b[1]))
        finally:
            self._drop(*a)
            self._drop(*b)

        assert result.failures == [], "\n".join(result.failures)
        assert result.debris == [], "\n".join(result.debris)
