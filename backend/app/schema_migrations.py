"""Which migrations has this database had? — ADR-181.

Migrations stay what `CODE-REVIEW-BRIEF.md` wants them to be: hand-written,
numbered files in `backend/scripts/`, meant to be read. What this module adds
is the half that choice left unpaid — a database now remembers which of those
files it has had, and the application refuses to start while one is pending.

The incident it answers (2026-09-20): `migrate_0019` renamed three `snapshots`
columns, the models moved, the development database did not, and signing in
returned a 500 four layers from the cause. A refusal at boot that names the
file replaces that.

**Nothing here applies a migration on its own.** Startup only checks. Applying
is `scripts/migrate.py --apply`, run by a person — the principle
`check_schema.py` states: a script that silently ALTERs a database holding real
work is a worse failure than the one it prevents.
"""
import importlib
import logging
import subprocess
import sys
from pathlib import Path

from sqlalchemy import Column, DateTime, String, func, inspect
from sqlalchemy.orm import Session

from app.database import Base

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "scripts"

# The three claims a row can make (ADR-181 point 1). Kept distinct because only
# RAN is evidence the file executed; the other two are a checked assertion and a
# consequence of how the database was made.
RAN = "ran"
BASELINE = "baseline"
BUILT = "built"


class SchemaMigrationDB(Base):
    """One row per migration file this database has had."""

    __tablename__ = "schema_migrations"

    filename = Column(String(255), primary_key=True)
    how = Column(String(20), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PendingMigrations(RuntimeError):
    """Raised at startup. The message is the whole remedy, so it names both the
    files and the command — somebody reading it at boot should not need this
    module open to know what to do."""


def migration_files(directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Every migration, in the order it must be applied (ADR-181 point 2).

    Ordered by filename, which is why the files carry zero-padded numbers and
    why `0001a` sorts before `0001b` before `0002`.
    """
    return sorted(
        p.name for p in directory.iterdir()
        if p.name.startswith("migrate_") and p.suffix in (".sql", ".py")
    )


def recorded(db: Session) -> dict[str, str]:
    return {row.filename: row.how for row in db.query(SchemaMigrationDB).all()}


def pending(db: Session, directory: Path = MIGRATIONS_DIR) -> list[str]:
    done = recorded(db)
    return [name for name in migration_files(directory) if name not in done]


def record(db: Session, filenames: list[str], how: str) -> None:
    """Record files as had. Idempotent: a file already recorded keeps its
    original `how`, because the first claim is the one that happened — a
    baseline must never overwrite the evidence of a run."""
    done = recorded(db)
    for name in filenames:
        if name not in done:
            db.add(SchemaMigrationDB(filename=name, how=how))
    db.commit()


def application_tables_exist(engine) -> bool:
    """Does this database hold any schema besides the ledger itself?

    Asked BEFORE `create_all` runs, because afterwards every database has
    tables. The answer is what separates a database being built from nothing
    (at head by construction, point 5) from an existing one whose history is
    unknown (point 6).
    """
    return bool(set(inspect(engine).get_table_names()) - {SchemaMigrationDB.__tablename__})


def assert_no_pending_migrations(
    db: Session, *, built_from_nothing: bool, directory: Path = MIGRATIONS_DIR,
) -> None:
    """The startup check (ADR-181 points 3, 5, 6 and 7).

    Refuses rather than warns: on 2026-09-20 the application started cleanly
    and failed on the first request that mattered, and a warning at boot would
    have been one more line nobody read before that request.
    """
    files = migration_files(directory)
    if built_from_nothing:
        # `create_all` just built every table from the models, so this schema
        # is what every migration was moving toward. Recording that is a
        # statement about how the database was made, and `built` says exactly
        # that rather than claiming anything ran.
        record(db, files, BUILT)
        return

    done = recorded(db)
    for orphan in sorted(set(done) - set(files)):
        # Point 7. Unusual and worth saying out loud, but refusing would be a
        # refusal nobody could satisfy — the file cannot be applied.
        logger.warning(
            "schema_migrations: %s is recorded as %s but is no longer in %s",
            orphan, done[orphan], directory,
        )

    missing = [name for name in files if name not in done]
    if not missing:
        return

    if not done:
        raise PendingMigrations(
            "This database has no migration ledger yet (ADR-181), so nothing "
            "says which migrations it has had. If it is current, record that:\n\n"
            "    venv/bin/python scripts/migrate.py --baseline\n\n"
            "The baseline runs check_schema first and refuses if the columns "
            "disagree with the models. It cannot check data migrations — you "
            "are asserting those ran."
        )
    raise PendingMigrations(
        "Migrations are pending, and the application will not start against a "
        "database that is behind its models (ADR-181):\n\n"
        + "".join(f"    {name}\n" for name in missing)
        + "\nApply them with:\n\n"
        "    venv/bin/python scripts/migrate.py --apply\n"
    )


def import_all_models() -> None:
    """Register every model on `Base.metadata` without importing `main`.

    Every model in this codebase lives in a module named `db_models`, so
    walking the package for them finds each one — including a new one nobody
    remembered to add to a list, which is the drop-in property ADR-160 point 6
    asks of modules.

    **Why not `import main`, which is what `check_schema.py` used to do:**
    importing `main` now runs the startup check, and on a database without a
    ledger that check refuses — so the command that creates the ledger could
    never run. `test_schema_migrations` asserts this walk registers the same
    tables `main` does.
    """
    # **The filesystem, not `pkgutil.walk_packages`.** `app/content/` and
    # `app/providers/` have no `__init__.py`, and pkgutil does not descend into
    # namespace packages — so the first version of this missed six tables,
    # including `content_records`, and the registration test caught it before
    # anything relied on it.
    app_root = Path(__file__).resolve().parent
    for path in sorted(app_root.rglob("db_models.py")):
        dotted = ".".join(("app",) + path.relative_to(app_root).with_suffix("").parts)
        importlib.import_module(dotted)


def apply_pending(
    db: Session, engine, directory: Path = MIGRATIONS_DIR,
) -> list[str]:
    """Run every pending file in order, recording each as it succeeds, and stop
    at the first failure (ADR-181 point 4). Returns what ran.

    **Each SQL file runs as one string, committed on success and rolled back
    on failure**, so a file is atomic whether or not it carries its own
    `BEGIN`/`COMMIT`. A file that manages its own transaction keeps that
    control; the runner's commit then has nothing left to do.

    **The first version set `autocommit` on the pooled connection instead, and
    every SQL file silently rolled back while being recorded as `ran`.**
    SQLAlchemy's pool proxy accepted the attribute without passing it to the
    driver, and returning the connection to the pool rolled the work back.
    `test_pending_files_run_in_order_and_are_recorded_as_ran` caught it by
    reading the data the files wrote rather than trusting the return value —
    the ledger and the database disagreeing is the one failure this module
    exists to make impossible.

    A Python migration runs as its own process with `--apply`, the convention
    0020 and 0021 already follow; a non-zero exit is a failure.
    """
    ran: list[str] = []
    for name in pending(db, directory):
        path = directory / name
        if path.suffix == ".sql":
            raw = engine.raw_connection()
            try:
                with raw.cursor() as cursor:
                    cursor.execute(path.read_text())
                raw.commit()
            except Exception:
                raw.rollback()
                raise
            finally:
                raw.close()
        else:
            completed = subprocess.run(
                [sys.executable, str(path), "--apply"],
                cwd=str(directory.parent),
            )
            if completed.returncode != 0:
                raise RuntimeError(f"{name} exited {completed.returncode}; stopped there")
        record(db, [name], RAN)
        ran.append(name)
    return ran


def baseline(db: Session, *, schema_matches: bool, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Record every unrecorded file as `baseline` (ADR-181 point 6).

    Refused unless the columns match the models, so an out-of-date database
    cannot be declared current by the command meant for current ones. The
    caller supplies `schema_matches` from `check_schema`, which keeps this
    function testable without a deliberately broken database.
    """
    if not schema_matches:
        raise RuntimeError(
            "Refusing to baseline: check_schema reports that this database "
            "disagrees with the models. Apply the missing migrations first."
        )
    missing = pending(db, directory)
    record(db, missing, BASELINE)
    return missing
