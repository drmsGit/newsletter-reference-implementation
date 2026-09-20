"""The indexes the models declare are the indexes the database has.

**Two creation paths, and they have disagreed before.** A test database is
built by `Base.metadata.create_all`; a deployed one is built by the migrations
in `backend/scripts/`. Nothing makes them agree, and when they drifted once
before — `pending_actions` losing its partial unique index because `create_all`
skips a table that already exists — the harness quietly enforced a different
schema from production and two tests started passing against a database that
could not have refused them.

This file checks the narrow version of that for two migrations: 0018's three
campaign-chain indexes, and 0019's three column renames. It is not a general
models-versus-migrations check; that is a larger piece of work and is logged.

A rename is the sharpest case of the drift, which is why 0019 is here. A
`create_all` database gets the new names because the models declare them; an
existing database gets them only if the migration runs. Nothing else would
notice the difference until a query on a deployed database failed on a column
that the whole test suite says exists.
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


# --- migration 0019, the snapshot artifact rename ---------------------------

MIGRATION_0019 = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts" / "migrate_0019_snapshot_artifact_columns.sql"
)

#: ADR-162 point 3. `html_*` described one of the two storage shapes and lied
#: about the other: a push payload's byte count in a column called `html_size`
#: is a name the next reader has to decode. Both branches write
#: `artifact.size_bytes()`, so the value always meant "the serialised
#: artifact", and only the name was channel-specific.
ARTIFACT_COLUMNS = {
    "html_storage_type": "artifact_storage_type",
    "html_location": "artifact_location",
    "html_size": "artifact_size",
}


def _snapshot_columns() -> set[str]:
    with engine.connect() as conn:
        return {
            row[0] for row in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'snapshots'"
            )).fetchall()
        }


def test_the_snapshot_columns_are_named_for_what_they_hold():
    columns = _snapshot_columns()
    missing = [new for new in ARTIFACT_COLUMNS.values() if new not in columns]
    lingering = [old for old in ARTIFACT_COLUMNS if old in columns]

    assert not missing, f"snapshots is missing {missing} — was it rebuilt from the models?"
    assert not lingering, (
        f"snapshots still has {lingering}. Both names existing at once is worse "
        "than either alone: two columns holding the same fact, and nothing "
        "saying which one a reader should trust."
    )


def test_migration_0019_renames_the_same_three():
    """The other creation path. A model-only rename leaves every existing
    deployment on the old names, and a migration-only rename leaves every new
    one on the new — either way the two disagree and only one is tested."""
    sql = MIGRATION_0019.read_text()
    missing = [
        f"{old} -> {new}" for old, new in ARTIFACT_COLUMNS.items()
        if f"RENAME COLUMN {old} TO {new}" not in sql
    ]
    assert not missing, (
        f"migration 0019 does not rename {missing}, but the models expect it."
    )
