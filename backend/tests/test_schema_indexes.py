"""The indexes the models declare are the indexes the database has.

**Two creation paths, and they have disagreed before.** A test database is
built by `Base.metadata.create_all`; a deployed one is built by the migrations
in `backend/scripts/`. Nothing makes them agree, and when they drifted once
before — `pending_actions` losing its partial unique index because `create_all`
skips a table that already exists — the harness quietly enforced a different
schema from production and two tests started passing against a database that
could not have refused them.

This file checks the narrow version of that for migration 0018: the three
campaign-chain indexes exist in the database the suite is running against, and
the migration names the same three. It is not a general models-versus-migrations
check; that is a larger piece of work and is logged.
"""
import pathlib

from sqlalchemy import text

from app.database import engine

MIGRATION = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "migrate_0018_campaign_chain_indexes.sql"

#: (table, column) pairs migration 0018 exists to index. Measured 2026-09-20 —
#: 36x, 83x and 111x respectively. A fourth candidate,
#: `delivery_executions.send_instance_id`, was measured at no improvement and
#: is deliberately absent: a send instance owns most of that table's rows, so
#: the lookup is unselective and a sequential scan is the right plan.
CHAIN_INDEXES = [
    ("variants", "campaign_id"),
    ("decision_slots", "variant_id"),
    ("decision_resolutions", "decision_slot_id"),
]


def _leading_columns() -> set[tuple[str, str]]:
    """Every (table, first-indexed-column) pair the live database has.

    The *leading* column, because that is what decides whether a lookup on it
    can use the index at all — and it is why `module_instances.variant_id` and
    `content_versions.content_record_id` need nothing of their own: both are
    already the first column of a composite unique constraint.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT t.relname, a.attname
            FROM pg_index i
            JOIN pg_class t ON t.oid = i.indrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = i.indkey[0]
        """)).fetchall()
    return {(t, c) for t, c in rows}


def test_the_campaign_chain_is_indexed_in_the_database():
    """The models declare these, so a rebuilt database must have them."""
    present = _leading_columns()
    missing = [f"{t}.{c}" for t, c in CHAIN_INDEXES if (t, c) not in present]
    assert not missing, (
        f"no index leads on {missing}. The models declare `index=True` on these "
        "columns; if the database does not have them it was not rebuilt from the "
        "models, and the suite is enforcing a different schema from production."
    )


def test_the_migration_names_the_same_three():
    """The other creation path, checked against the same list.

    Declaring an index in the model alone gives it to every NEW database and to
    none of the existing ones. Declaring it in the migration alone gives it to
    every existing database and to none of the new ones. Both, or the two paths
    build different schemas — which is the failure this file exists for.
    """
    sql = MIGRATION.read_text()
    missing = [
        f"{t}.{c}" for t, c in CHAIN_INDEXES
        if f"ON {t} ({c})" not in sql
    ]
    assert not missing, (
        f"migration 0018 does not create an index on {missing}, but the models "
        "declare one. An existing deployment would never get it."
    )
