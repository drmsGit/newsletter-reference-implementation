"""Drop every snapshot made before ADR-183, and what hangs off it.

Run from `backend/`:

    venv/bin/python scripts/drop_frameless_snapshots.py           # dry run: counts only
    venv/bin/python scripts/drop_frameless_snapshots.py --apply   # delete

A snapshot made before 2026-10-02 holds no frame, so it cannot be sent
(`send_send_instance` refuses it) or previewed. Decided 2026-10-02: this is not
a live environment, so such snapshots are dropped rather than kept in a refused
state — make new campaigns instead.

**What goes, in foreign-key order** (`tests/test_drop_frameless_snapshots.py`
fails if a new foreign key appears that this script does not handle):

  - signal contributions learned from those sends' engagement events — the
    profile loses what those sends taught it, which is the honest consequence
    of dropping the sends;
  - the engagement events, the delivery executions, the send instances;
  - the snapshots themselves;
  - every `storage/snapshots/*.html` file: since ADR-183 nothing reads them.

Content overrides that name one of those sends keep existing and lose only the
link (`send_instance_id` set to NULL); an override is an edit, not a send.

A dry run is the default, because the other mode deletes data.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB  # noqa: E402
from app.insight.db_models import EngagementEventDB  # noqa: E402
from app.overrides.db_models import ContentOverrideDB  # noqa: E402
from app.recipients.db_models import SignalContributionDB  # noqa: E402
from app.rendering.frame import is_frame  # noqa: E402
from app.snapshots.db_models import SnapshotDB  # noqa: E402

STORAGE = Path(__file__).resolve().parents[2] / "storage" / "snapshots"


def plan(db, storage: Path = STORAGE):
    """The ids that would go, as a dict of lists — computed, not deleted.
    `storage` is a parameter so a test can point it away from the real files."""
    snapshots = [s.id for s in db.query(SnapshotDB).all() if not is_frame(s.render_context)]
    sends = [s.id for s in db.query(SendInstanceDB.id).filter(
        SendInstanceDB.snapshot_id.in_(snapshots))] if snapshots else []
    executions = [e.id for e in db.query(DeliveryExecutionDB.id).filter(
        DeliveryExecutionDB.send_instance_id.in_(sends))] if sends else []
    events = [e.id for e in db.query(EngagementEventDB.id).filter(
        EngagementEventDB.delivery_execution_id.in_(executions))] if executions else []
    contributions = [c.id for c in db.query(SignalContributionDB.id).filter(
        SignalContributionDB.event_id.in_(events))] if events else []
    overrides = [o.id for o in db.query(ContentOverrideDB.id).filter(
        ContentOverrideDB.send_instance_id.in_(sends))] if sends else []
    return {
        "snapshots": snapshots, "send_instances": sends, "delivery_executions": executions,
        "engagement_events": events, "signal_contributions": contributions,
        "overrides_unlinked": overrides,
        "html_files": sorted(storage.glob("*.html")) if storage.exists() else [],
    }


def apply(db, ids) -> None:
    db.query(ContentOverrideDB).filter(ContentOverrideDB.id.in_(ids["overrides_unlinked"])).update(
        {"send_instance_id": None}, synchronize_session=False)
    for model, key in (
        (SignalContributionDB, "signal_contributions"),
        (EngagementEventDB, "engagement_events"),
        (DeliveryExecutionDB, "delivery_executions"),
        (SendInstanceDB, "send_instances"),
        (SnapshotDB, "snapshots"),
    ):
        if ids[key]:
            db.query(model).filter(model.id.in_(ids[key])).delete(synchronize_session=False)
    db.commit()
    for path in ids["html_files"]:
        path.unlink(missing_ok=True)


def main() -> int:
    db = SessionLocal()
    try:
        ids = plan(db)
        for key, values in ids.items():
            print(f"  {key:22} {len(values)}")
        if "--apply" not in sys.argv:
            print("\nDry run. Nothing was changed. Run with --apply to delete.")
            return 0
        apply(db, ids)
        print("\nDone.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
