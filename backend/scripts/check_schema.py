"""Does the database this app is pointed at match the models?

    venv/bin/python -m scripts.check_schema

**Why this exists.** There is no migration runner and no applied-state
tracking — that is the "no Alembic" choice in `CODE-REVIEW-BRIEF.md`, taken
deliberately, and this is the half of the bill nobody had paid. Migrations in
`backend/scripts/` are applied by hand, and **nothing tells you one is
pending**: the test suite rebuilds its own database from the models every run,
so it is green whatever the deployed database looks like.

On 2026-09-20 that cost a morning. `migrate_0019` renamed three `snapshots`
columns; the models were updated, the tests passed, and the dev database was
not migrated — so every query touching snapshots failed, which included the one
the dashboard runs on sign-in. Signing in returned a 500 and the cause was four
layers from the symptom.

**This is a detector, not a runner.** It reports what is missing and does not
apply anything, because a script that silently ALTERs a database holding real
work is a worse failure than the one it prevents. Run it, read it, apply the
migration named in the output.

Exits 1 when the schemas disagree, so CI can use it when there is CI.
"""
import sys

from sqlalchemy import inspect

import main  # noqa: F401 — imports every router, and therefore every model
from app.database import Base, engine


def main_() -> int:
    database = str(engine.url).rsplit("/", 1)[-1]
    inspector = inspect(engine)
    live_tables = set(inspector.get_table_names())

    missing_tables: list[str] = []
    differences: list[str] = []

    for table, model in sorted(Base.metadata.tables.items()):
        if table not in live_tables:
            missing_tables.append(table)
            continue
        live = {column["name"] for column in inspector.get_columns(table)}
        declared = {column.name for column in model.columns}
        if declared - live:
            differences.append(
                f"  {table}: the models expect {sorted(declared - live)} and the "
                "database does not have them"
            )
        if live - declared:
            # Not always a problem — a column the models dropped may be
            # deliberate debris awaiting a cleanup migration. Reported anyway,
            # because "deliberate" should be a decision somebody remembers
            # making.
            differences.append(
                f"  {table}: the database has {sorted(live - declared)} and the "
                "models do not declare them"
            )

    print(f"schema check: {database}")
    if not missing_tables and not differences:
        print("  models and database agree.")
        return 0

    if missing_tables:
        print("\ntables the models declare and the database lacks:")
        for table in missing_tables:
            print(f"  {table}")
    if differences:
        print("\ncolumn differences:")
        for line in differences:
            print(line)
    print(
        "\nThis usually means a migration in backend/scripts/ has not been "
        "applied to this database. Find the one that names these columns and "
        "run it — they are guarded and safe to re-run."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main_())
