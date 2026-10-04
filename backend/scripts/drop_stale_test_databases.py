"""List — and with `--drop`, remove — test databases whose checkout is gone (task-259).

Run from `backend/`:

    venv/bin/python scripts/drop_stale_test_databases.py          # list only
    venv/bin/python scripts/drop_stale_test_databases.py --drop   # and drop them

Every checkout's suite has a database of its own (`tests/checkout_database.py`)
and records the checkout's path as that database's comment on every run. A
worktree that is deleted leaves its database behind; this finds those by the
path no longer existing, plus the ones that record no path at all — the single
shared `<dev>_test` from before task-259.

**Listing is the default** because dropping deletes, and a command that
deletes when given no arguments is how people lose work. It never runs on its
own (decided with the user, 2026-10-04): a suite clearing other checkouts'
databases could hit one mid-run. Even with `--drop` a database somebody is
connected to is not forced — Postgres refuses, and that is reported, not
overridden. The dev database is never a candidate: only `<dev>_test` and
`<dev>_test_*` are considered, and the dev name is refused again before a drop.
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.checkout_database import (  # noqa: E402
    NAMED_BY_HAND, database_name, dev_database_url, test_database_name, test_database_prefix,
)


def _like_prefix(prefix: str) -> str:
    """`<prefix>_%` as a LIKE pattern, its own `_` and `%` taken literally."""
    escaped = prefix.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
    return escaped + "\\_%"


def candidates(cursor, dev_name: str) -> list[tuple[str, str | None]]:
    """Every test database beside this dev database, with its recorded checkout."""
    prefix = test_database_prefix(dev_name)
    cursor.execute(
        "SELECT d.datname, shobj_description(d.oid, 'pg_database') FROM pg_database d "
        "WHERE d.datname = %s OR d.datname LIKE %s ESCAPE '\\' ORDER BY d.datname",
        (prefix, _like_prefix(prefix)),
    )
    return [(name, comment) for name, comment in cursor.fetchall() if name != dev_name]


def stale(rows, dev_name: str, exists=lambda path: Path(path).exists()) -> list[tuple[str, str]]:
    """The leftovers among `rows`, each with why it counts as one: no checkout
    recorded, a checkout that is gone, or a name that checkout no longer uses
    (the naming changed since, so its suite runs on another database now)."""
    out = []
    for name, comment in rows:
        if comment and comment.endswith(NAMED_BY_HAND):
            continue  # somebody chose this name with TEST_DATABASE_URL; theirs to drop
        if not comment:
            out.append((name, "records no checkout (made before task-259)"))
        elif not exists(comment):
            out.append((name, f"its checkout {comment} is gone"))
        elif name != test_database_name(dev_name, Path(comment)):
            out.append((name, f"{comment} now uses {test_database_name(dev_name, Path(comment))}"))
    return out


def drop(cursor, names: list[str], dev_name: str) -> list[str]:
    """Drop each database in `names`; return the ones Postgres refused.

    Never forced: one somebody is connected to — a suite mid-run — stays, and
    is reported. The dev name is refused outright, although `candidates` can
    never return it, because this is the line that would destroy real work.
    """
    import psycopg2

    refused = []
    for name in names:
        if name == dev_name or not name.startswith(test_database_prefix(dev_name)):
            raise RuntimeError(f"refusing to drop {name!r}: not a test database")
        try:
            cursor.execute(f'DROP DATABASE "{name}"')
            print(f"  dropped {name}")
        except psycopg2.Error as error:
            refused.append(name)
            print(f"  could not drop {name}: {(error.pgerror or str(error)).strip()}")
    return refused


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--drop", action="store_true", help="drop the stale databases listed")
    args = parser.parse_args(argv)

    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    dev_url = dev_database_url()
    dev_name = database_name(dev_url)
    admin = urlunsplit(urlsplit(dev_url)._replace(path="/postgres"))
    connection = psycopg2.connect(admin)
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    failed = 0
    try:
        with connection.cursor() as cursor:
            rows = candidates(cursor, dev_name)
            leftovers = stale(rows, dev_name)
            print(f"{len(rows)} test database(s) beside {dev_name!r}; {len(leftovers)} stale.")
            for name, why in leftovers:
                print(f"  {name}: {why}")
            if not args.drop:
                if leftovers:
                    print("Nothing dropped. Run again with --drop to drop these.")
                return 0
            failed = len(drop(cursor, [name for name, _ in leftovers], dev_name))
    finally:
        connection.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
