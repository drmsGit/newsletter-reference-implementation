"""Apply, baseline or report migrations — ADR-181.

Run from `backend/`:

    venv/bin/python scripts/migrate.py              # status: what is recorded, what is pending
    venv/bin/python scripts/migrate.py --apply      # run pending files in order, stop at the first failure
    venv/bin/python scripts/migrate.py --baseline   # record an existing, current database

**Status is the default** because the other two change a database, and a
command that changes one when given no arguments is how people lose work.

The logic lives in `app/schema_migrations.py`; this is the part a person runs.
**The application never calls it.** Startup only checks, and refuses while a
file is pending — applying is a decision somebody makes, with this.

`--apply` against an empty database is not a supported path. Several old
migrations assume a populated one (0012 encodes a row count measured on the
development database), and a fresh database comes from the models instead —
`main.py` records it as `built` when it creates one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import schema_migrations as ledger  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402

# Registers every model, and so creates the ledger table if this database has
# none yet — the one table this command needs before it can say anything.
ledger.import_all_models()
ledger.SchemaMigrationDB.__table__.create(bind=engine, checkfirst=True)


def _status(db) -> int:
    done = ledger.recorded(db)
    files = ledger.migration_files()
    for name in files:
        print(f"  {done.get(name, 'PENDING'):9} {name}")
    for orphan in sorted(set(done) - set(files)):
        print(f"  {done[orphan]:9} {orphan}   (no longer on disk)")
    missing = [n for n in files if n not in done]
    if not done:
        print("\nNo ledger yet. If this database is current, run --baseline.")
    elif missing:
        print(f"\n{len(missing)} pending. Run --apply.")
    else:
        print("\nUp to date.")
    return 1 if missing else 0


def main() -> int:
    with SessionLocal() as db:
        if "--apply" in sys.argv:
            if not ledger.recorded(db):
                # An existing database with no ledger would otherwise have every
                # historical migration re-run against it, most of which are not
                # safe to run twice on real data.
                print(
                    "Refusing to apply: this database has no ledger, so every "
                    "migration would look pending. Run --baseline first."
                )
                return 1
            ran = ledger.apply_pending(db, engine)
            print("\n".join(f"  ran {name}" for name in ran) or "  nothing pending.")
            # Verify, now: this is the moment a migration either reached the
            # models' schema or did not (ADR-181 addendum, task-12). The files
            # ran and are recorded either way — a failed check does not undo
            # them — but a gap is reported here rather than found later.
            from scripts import check_schema

            print()
            return check_schema.main_()

        if "--baseline" in sys.argv:
            from scripts import check_schema

            matches = check_schema.main_() == 0
            try:
                recorded = ledger.baseline(db, schema_matches=matches)
            except RuntimeError as refusal:
                print(f"\n{refusal}")
                return 1
            print(f"\nRecorded {len(recorded)} file(s) as baseline.")
            print(
                "A baseline checks columns, not data. The Python data "
                "migrations (0020 onwards) are recorded on your word that they "
                "ran — the row says 'baseline', not 'ran', so it stays visible."
            )
            return 0

        return _status(db)


if __name__ == "__main__":
    raise SystemExit(main())
