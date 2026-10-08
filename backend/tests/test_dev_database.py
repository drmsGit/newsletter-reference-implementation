"""The dev database carries no product name, and its three descriptions agree (task-288).

Decided with the user 2026-10-08: name-free — database `app`, role
`app_user` — per task-29's rule "where a name adds nothing, use none", so a
second product rename never reaches it; and no fixed container name, since a
container name is unique across the whole machine and Compose already derives
one per checkout. The database is described in three places that must agree:
`docker-compose.yml` (what a fresh volume is initialised with), the app's
fallback URL (`app/database.py`) and the suite's (`tests/checkout_database.py`),
which is also what test databases are named after.
"""
import re
from pathlib import Path
from urllib.parse import urlsplit

from tests import checkout_database as checkout

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "docker-compose.yml").read_text()


def _compose(key: str) -> str:
    match = re.search(rf"^\s*{key}:\s*(\S+)\s*$", COMPOSE, re.MULTILINE)
    assert match, f"{key} missing from docker-compose.yml"
    return match.group(1)


def test_the_dev_database_is_name_free():
    url = urlsplit(checkout.DEV_DEFAULT)
    assert (url.path.lstrip("/"), url.username, url.password) == ("app", "app_user", "app_password")


def test_compose_initialises_what_the_fallback_urls_connect_to():
    url = urlsplit(checkout.DEV_DEFAULT)
    assert (_compose("POSTGRES_DB"), _compose("POSTGRES_USER"), _compose("POSTGRES_PASSWORD")) == (
        url.path.lstrip("/"), url.username, url.password)
    assert f'"{checkout.DEV_DEFAULT}"' in (ROOT / "backend/app/database.py").read_text(), (
        "the app's fallback URL and the suite's must be the same database")


def test_the_container_is_named_by_compose_not_by_hand():
    assert "container_name" not in COMPOSE


def test_test_databases_are_named_after_it(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    assert checkout.database_name(checkout.test_database_url()).startswith("app_test_")
