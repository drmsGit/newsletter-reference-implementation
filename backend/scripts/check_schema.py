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

**Since 2026-09-29 it has two callers** (ADR-181 and its addendum):
`scripts/migrate.py --baseline` refuses to record a baseline while this reports
a difference, and `--apply` runs it after applying. The ledger answers "which
migrations has this database had"; this answers "does it hold the schema the
models declare" — compared in full against a scratch database built from them.

**This is a detector, not a runner.** It reports what is missing and does not
apply anything, because a script that silently ALTERs a database holding real
work is a worse failure than the one it prevents. Run it, read it, apply the
migration named in the output.

Exits 1 when the schemas disagree, so CI can use it when there is CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine  # noqa: E402
from app.schema_compare import CannotCompare, check, report  # noqa: E402


def main_() -> int:
    """0 when the database holds the models' schema; 1 when it is behind or
    disagrees, or when there is nothing to compare it with.

    **Full comparison since 2026-09-29** (task-12). This used to compare column
    NAMES, and the development database passed it while carrying fourteen
    differences — eight defaults the models did not declare, three missing
    indexes — including an `audience_resolution_mode` defaulting to the
    `'freeze'` that ADR-176 had removed that morning. `migrate.py --baseline`
    gates on this, so a weak check here was a weak baseline.

    Debris (only in the database) is printed and does not fail.
    """
    database = engine.url.database
    try:
        result = check(engine)
    except CannotCompare as refusal:
        print(f"schema check: {database}\n  {refusal}")
        return 1
    print(report(result, database))
    return 0 if result.agrees else 1


if __name__ == "__main__":
    sys.exit(main_())
