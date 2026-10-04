"""Each checkout's suite runs on a database of its own (task-259).

One `newsletter_test` shared by every worktree let two suites running at once
rebuild the schema under each other: on 2026-10-03 a run failed 86 tests with a
column another checkout's models did not have. The name is now per checkout,
the checkout is recorded on the database, and leftovers are listed — and
dropped only when asked — by `scripts/drop_stale_test_databases.py`.
"""
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from scripts import drop_stale_test_databases as cleanup
from tests import checkout_database as checkout
from tests.conftest import (
    DEV_DATABASE_URL, TEST_DATABASE_URL, _ensure_database_exists, _refuse_the_dev_database,
)


class TestTheName:
    def test_two_checkouts_with_the_same_folder_name_get_different_databases(self):
        a = checkout.test_database_name("newsletter", Path("/work/one/newsletter"))
        b = checkout.test_database_name("newsletter", Path("/work/two/newsletter"))
        assert a != b
        assert a == checkout.test_database_name("newsletter", Path("/work/one/newsletter")), "stable per checkout"

    def test_it_reads_as_its_folder_and_stays_a_legal_identifier(self):
        name = checkout.test_database_name("newsletter", Path("/w/Feature: Fix #12 (draft)"))
        assert re.fullmatch(r"newsletter_test_feature_fix_12_draft_[0-9a-f]{6}", name), name

    def test_a_long_folder_is_shortened_and_the_hash_kept(self):
        root = Path("/w/" + "very-long-worktree-name-" * 6)
        name = checkout.test_database_name("newsletter", root)
        assert len(name) <= checkout.MAX_NAME
        assert name.endswith("_" + checkout.test_database_name("newsletter", root)[-6:])
        assert name != checkout.test_database_name("newsletter", Path("/x/" + "very-long-worktree-name-" * 6))

    def test_this_suite_runs_on_this_checkouts_database(self):
        explicit = checkout.os.environ.get("TEST_DATABASE_URL")
        expected = checkout.database_name(explicit) if explicit else checkout.test_database_name(
            checkout.database_name(DEV_DATABASE_URL), checkout.checkout_root()
        )
        assert checkout.database_name(TEST_DATABASE_URL) == expected

    def test_test_database_url_still_wins_and_is_recorded_as_chosen(self, monkeypatch):
        monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://u:p@h:5432/mine")
        assert checkout.test_database_url() == "postgresql://u:p@h:5432/mine"
        assert checkout.recorded_checkout().endswith(checkout.NAMED_BY_HAND)
        monkeypatch.delenv("TEST_DATABASE_URL")
        assert checkout.recorded_checkout() == str(checkout.checkout_root())


class TestTheDevDatabaseIsStillRefused:
    """AC 2: the guard keeps its guarantee whatever the naming does."""

    def test_the_dev_name_is_refused(self):
        with pytest.raises(RuntimeError, match="development database"):
            _refuse_the_dev_database(checkout.DEV_DEFAULT)

    def test_a_derived_name_is_never_the_dev_name(self):
        dev = checkout.database_name(checkout.DEV_DEFAULT)
        assert checkout.test_database_name(dev, Path("/w/newsletter")) != dev


def _admin():
    connection = psycopg2.connect(urlunsplit(urlsplit(TEST_DATABASE_URL)._replace(path="/postgres")))
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return connection


@pytest.fixture
def throwaway():
    """Test databases made for this test only, so dropping one is never
    somebody's leftover. Removed afterwards whatever happened."""
    dev = checkout.database_name(DEV_DATABASE_URL)
    made = []
    connection = _admin()

    def make(comment):
        name = f"{checkout.test_database_prefix(dev)}_zz{uuid.uuid4().hex[:8]}"
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{name}"')
            if comment is not None:
                cursor.execute(f'COMMENT ON DATABASE "{name}" IS %s', (comment,))
        made.append(name)
        return name

    yield dev, connection, make
    with connection.cursor() as cursor:
        for name in made:
            cursor.execute(f'DROP DATABASE IF EXISTS "{name}"')
    connection.close()


class TestTheCleanup:
    def test_the_suite_records_its_checkout_on_its_database(self):
        """Cleared first, so a comment left by an earlier run cannot pass it."""
        name = checkout.database_name(TEST_DATABASE_URL)
        connection = _admin()
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'COMMENT ON DATABASE "{name}" IS NULL')
                _ensure_database_exists(TEST_DATABASE_URL)
                cursor.execute(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = %s",
                    (name,),
                )
                assert cursor.fetchone()[0] == checkout.recorded_checkout()
        finally:
            connection.close()

    def test_a_gone_checkout_or_none_recorded_is_stale_and_a_live_one_is_not(self, throwaway):
        dev, connection, make = throwaway
        gone = make("/nowhere/a-deleted-worktree")
        unrecorded = make(None)
        renamed = make(str(checkout.checkout_root()))  # a live checkout, but not the name it uses now
        by_hand = make(str(checkout.checkout_root()) + checkout.NAMED_BY_HAND)
        with connection.cursor() as cursor:
            found = dict(cleanup.stale(cleanup.candidates(cursor, dev), dev))
        assert "is gone" in found[gone]
        assert "records no checkout" in found[unrecorded]
        assert "now uses" in found[renamed]
        assert by_hand not in found, "a name somebody chose with TEST_DATABASE_URL is theirs to drop"
        assert checkout.database_name(TEST_DATABASE_URL) not in found, "this run's own database"
        assert dev not in found

    def test_drop_removes_a_stale_one_and_never_forces_one_in_use(self, throwaway):
        dev, connection, make = throwaway
        stale, busy = make("/nowhere/one"), make("/nowhere/two")
        holder = psycopg2.connect(urlunsplit(urlsplit(TEST_DATABASE_URL)._replace(path=f"/{busy}")))
        try:
            with connection.cursor() as cursor:
                refused = cleanup.drop(cursor, [stale, busy], dev)
                cursor.execute("SELECT datname FROM pg_database WHERE datname IN (%s, %s)", (stale, busy))
                left = {row[0] for row in cursor.fetchall()}
        finally:
            holder.close()
        assert refused == [busy]
        assert left == {busy}

    def test_drop_refuses_anything_but_a_test_database(self, throwaway):
        """**Names that do not exist, on purpose.** An earlier version passed
        the real dev name, so a mutant with the guard removed made this test
        try to drop the dev database; only an open connection stopped
        Postgres. With made-up names a broken guard fails the test with a
        "does not exist" refusal and can destroy nothing."""
        _, connection, _ = throwaway
        fake_dev = f"zz_not_a_dev_db_{uuid.uuid4().hex[:8]}"
        with connection.cursor() as cursor:
            for name in (fake_dev, f"zz_unrelated_{uuid.uuid4().hex[:8]}"):
                with pytest.raises(RuntimeError, match="not a test database"):
                    cleanup.drop(cursor, [name], fake_dev)
