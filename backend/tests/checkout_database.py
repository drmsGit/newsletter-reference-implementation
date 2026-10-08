"""Which test database a checkout uses (task-259).

Every checkout — the main one, each git worktree, a second clone — gets a
database of its own, because the suite is destructive by design: it drops and
rebuilds the schema at load (`conftest._start_from_an_empty_schema`). One name
shared by every checkout let two suites running at once rebuild the schema
under each other, from different models, and fail each other's tests.

The name is `<dev>_test_<folder>_<hash>`: the folder for a person reading a
list of databases, six hex characters of the checkout's absolute path so two
folders with the same name never meet. Postgres cuts identifiers at 63 bytes,
so the folder part is shortened to fit rather than the name being truncated
somewhere the hash would be lost.

Pure standard library, and importing it touches no database: `conftest.py`
uses it before anything imports `app.database`, and
`scripts/drop_stale_test_databases.py` uses it to know what a test database is
called. The name does not start with `test_`, so pytest does not collect it.
"""
import hashlib
import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

#: The dev database, which the suite must never touch.
DEV_DEFAULT = (
    "postgresql://app_user:app_password@localhost:5432/app"
)

#: Postgres's identifier limit (NAMEDATALEN - 1).
MAX_NAME = 63

#: Appended to the recorded checkout when `TEST_DATABASE_URL` named the
#: database: somebody chose that name, so the cleanup script never counts it
#: as a leftover — whoever named it drops it.
NAMED_BY_HAND = " (named by TEST_DATABASE_URL)"


def recorded_checkout() -> str:
    """What the suite writes as its database's comment."""
    return str(checkout_root()) + (NAMED_BY_HAND if os.environ.get("TEST_DATABASE_URL") else "")


def checkout_root() -> Path:
    """The checkout this file sits in: `<root>/backend/tests/checkout_database.py`."""
    return Path(__file__).resolve().parents[2]


def dev_database_url() -> str:
    return os.environ.get("DATABASE_URL") or DEV_DEFAULT


def database_name(url: str) -> str:
    return urlsplit(url).path.lstrip("/")


def test_database_prefix(dev_name: str) -> str:
    """What every derived test database name starts with."""
    return f"{dev_name}_test"


def test_database_name(dev_name: str, root: Path) -> str:
    """`<dev>_test_<folder slug>_<6-hex path hash>`, at most 63 characters."""
    digest = hashlib.sha256(str(root).encode()).hexdigest()[:6]
    head = f"{test_database_prefix(dev_name)}_"
    slug = re.sub(r"[^a-z0-9]+", "_", root.name.lower()).strip("_") or "checkout"
    room = MAX_NAME - len(head) - 1 - len(digest)
    slug = slug[:room].rstrip("_") if room > 0 else ""
    return f"{head}{slug}_{digest}" if slug else f"{head}{digest}"


def test_database_url() -> str:
    """Where this checkout's suite runs. `TEST_DATABASE_URL` still wins."""
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    parts = urlsplit(dev_database_url())
    name = test_database_name(database_name(dev_database_url()), checkout_root())
    return urlunsplit(parts._replace(path=f"/{name}"))
