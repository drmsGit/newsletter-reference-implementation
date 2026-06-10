from sqlalchemy.orm import Session

from app.rendering.service import render_variant_html
from app.snapshots.db_models import SnapshotDB
from app.snapshots.models import Snapshot


def to_snapshot(record: SnapshotDB) -> Snapshot:
    return Snapshot(
        id=record.id,
        variant_id=record.variant_id,
        html=record.html,
        created_at=record.created_at,
    )


def create_snapshot_for_variant(db: Session, variant_id: int) -> Snapshot:
    html = render_variant_html(db=db, variant_id=variant_id)

    snapshot = SnapshotDB(
        variant_id=variant_id,
        html=html,
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return to_snapshot(snapshot)


def list_snapshots_for_variant(db: Session, variant_id: int) -> list[Snapshot]:
    records = (
        db.query(SnapshotDB)
        .filter(SnapshotDB.variant_id == variant_id)
        .order_by(SnapshotDB.created_at.desc())
        .all()
    )

    return [to_snapshot(record) for record in records]