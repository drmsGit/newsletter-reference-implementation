"""Does a database hold the schema the models declare? — task-12, ADR-181 addendum.

A database built by `create_all` and one built by the migrations in
`backend/scripts/` must agree, and nothing made them. The literal check — build
a database both ways and diff them — cannot be done here: the migrations are
deltas over a schema `create_all` built around 2026-09-12 that no file records,
so they cannot build a database from empty. The migrations path exists only as
real databases. So this compares a real database against a **scratch database
built from the models**, and drops the scratch one afterwards.

The first run against the development database found fourteen differences the
old column-name check could not see: eight server-side defaults the models did
not declare — three of them fail-open (`audience_resolution_mode` defaulting to
the removed `'freeze'`, a channel defaulting to `'email'`, a purpose to
`'marketing'`) — three `pending_actions` indexes from migration 0017 that test
databases never had, and a redundant index.

**Two kinds of difference, and only one fails.** *Behind or disagreeing*:
anything the models declare that the database lacks or holds differently.
*Debris*: something only the database has — reported, because "deliberate"
should be a decision somebody remembers making, but not failed.
"""
import re
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url


@dataclass
class Comparison:
    failures: list[str] = field(default_factory=list)
    debris: list[str] = field(default_factory=list)

    @property
    def agrees(self) -> bool:
        return not self.failures


def describe(engine: Engine) -> dict:
    """Every table's columns, indexes and constraints, with names removed.

    Names are removed because the two paths name things differently — the
    migrations say `ux_…`, a model's `unique=True` says `ix_…` — and a name is
    not a rule. What must agree is what the database will enforce.
    """
    tables: dict[str, dict] = {}

    def table(name):
        return tables.setdefault(name, {"columns": {}, "indexes": set(), "constraints": set()})

    with engine.connect() as c:
        for t, col, typ, length, nullable, default in c.execute(text("""
            SELECT table_name, column_name, udt_name, character_maximum_length,
                   is_nullable, column_default
            FROM information_schema.columns WHERE table_schema = 'public'""")):
            if default:
                # A serial column's sequence is named after its table in both
                # paths, but the name is incidental; that it is one is not.
                default = re.sub(r"nextval\('[^']+'::regclass\)", "nextval(sequence)", default)
            table(t)["columns"][col] = (
                typ + (f"({length})" if length else ""), nullable == "YES", default,
            )
        for t, definition in c.execute(text(
                "SELECT tablename, indexdef FROM pg_indexes WHERE schemaname = 'public'")):
            table(t)["indexes"].add(
                re.sub(r"INDEX \S+ ON public\.\S+ ", "INDEX ", definition).replace("public.", "")
            )
        for t, kind, definition in c.execute(text("""
            SELECT cl.relname, co.contype, pg_get_constraintdef(co.oid)
            FROM pg_constraint co
            JOIN pg_class cl ON cl.oid = co.conrelid
            JOIN pg_namespace n ON n.oid = cl.relnamespace
            WHERE n.nspname = 'public'""")):
            # A UNIQUE constraint and a unique index are the same rule: the
            # constraint's backing index is already compared above, so the
            # constraint itself is not. The migrations write constraints and a
            # model's `unique=True, index=True` writes an index; both refuse
            # the duplicate.
            if kind != "u":
                table(t)["constraints"].add((kind, definition))
    return tables


def compare(live: dict, models: dict) -> Comparison:
    result = Comparison()
    for t in sorted(set(live) | set(models)):
        if t not in live:
            result.failures.append(f"table {t}: declared by the models, missing from the database")
            continue
        if t not in models:
            result.debris.append(f"table {t}: in the database, not declared by any model")
            continue
        have, want = live[t], models[t]
        for col in sorted(set(have["columns"]) | set(want["columns"])):
            h, w = have["columns"].get(col), want["columns"].get(col)
            if w is None:
                result.debris.append(f"{t}.{col}: in the database, not declared by the models")
            elif h is None:
                result.failures.append(f"{t}.{col}: declared by the models, missing from the database")
            elif h != w:
                result.failures.append(
                    f"{t}.{col}: database has {_column(h)}, the models declare {_column(w)}"
                )
        for index in sorted(want["indexes"] - have["indexes"]):
            result.failures.append(f"{t}: the models declare {index}, the database lacks it")
        for index in sorted(have["indexes"] - want["indexes"]):
            result.debris.append(f"{t}: {index} exists only in the database")
        for kind, definition in sorted(want["constraints"] - have["constraints"]):
            result.failures.append(f"{t}: the models declare {definition}, the database lacks it")
        for kind, definition in sorted(have["constraints"] - want["constraints"]):
            result.failures.append(
                f"{t}: the database enforces {definition}, the models do not declare it"
            )
    return result


def _column(spec) -> str:
    typ, nullable, default = spec
    return f"{typ} {'NULL' if nullable else 'NOT NULL'}" + (f" DEFAULT {default}" if default else "")


@contextmanager
def models_database(live: Engine):
    """A throwaway database on the same server, built from the models.

    Created and dropped here, never reused: a scratch database left behind by an
    earlier run is dropped first, because a stale one would compare the live
    database against yesterday's models. Refuses to touch the live database by
    name, whatever the naming produces.
    """
    from app.database import Base
    from app.schema_migrations import import_all_models

    url = make_url(live.url.render_as_string(hide_password=False))
    scratch = f"{url.database}_schemacheck"
    assert scratch != url.database
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)'))
            c.execute(text(f'CREATE DATABASE "{scratch}"'))
    except Exception as error:
        admin.dispose()
        raise CannotCompare(
            f"could not create a scratch database to compare against ({error.__class__.__name__}). "
            "The check needs permission to create a database; without it there is "
            "nothing to compare with, and that is reported rather than passed."
        ) from error
    built = create_engine(url.set(database=scratch))
    try:
        import_all_models()
        Base.metadata.create_all(bind=built)
        yield built
    finally:
        built.dispose()
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)'))
        admin.dispose()


class CannotCompare(RuntimeError):
    pass


def check(live: Engine) -> Comparison:
    """Compare a live database with the models' schema."""
    with models_database(live) as built:
        return compare(describe(live), describe(built))


def report(result: Comparison, database: str) -> str:
    lines = [f"schema check: {database}"]
    if result.agrees and not result.debris:
        lines.append("  models and database agree.")
    for line in result.failures:
        lines.append(f"  DIFFERS  {line}")
    for line in result.debris:
        lines.append(f"  debris   {line}")
    if result.failures:
        lines.append(
            "\nThe database is behind the models or disagrees with them. Usually a "
            "migration in backend/scripts/ has not been applied; if none is "
            "pending, a migration is needed to bring the two together."
        )
    return "\n".join(lines)
