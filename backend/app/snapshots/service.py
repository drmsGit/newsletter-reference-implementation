from pathlib import Path

from sqlalchemy.orm import Session

from app.rendering.service import render_variant_html
from app.snapshots.db_models import SnapshotDB
from app.snapshots.models import Snapshot


SNAPSHOT_STORAGE_DIR = Path("../storage/snapshots")


def to_snapshot(record: SnapshotDB) -> Snapshot:
    return Snapshot(
        id=record.id,
        variant_id=record.variant_id,
        html_storage_type=record.html_storage_type,
        html_location=record.html_location,
        html_size=record.html_size,
        created_at=record.created_at,
    )


def create_snapshot_for_variant(db: Session, variant_id: int) -> Snapshot:
    html = render_variant_html(db=db, variant_id=variant_id)

    SNAPSHOT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = SnapshotDB(
        variant_id=variant_id,
        html_storage_type="file",
        html_location="pending",
        html_size=len(html.encode("utf-8")),
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    file_name = f"variant-{variant_id}-snapshot-{snapshot.id}.html"
    file_path = SNAPSHOT_STORAGE_DIR / file_name
    file_path.write_text(html, encoding="utf-8")

    snapshot.html_location = str(file_path)
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


def get_snapshot_html(db: Session, snapshot_id: int) -> str | None:
    snapshot = (
        db.query(SnapshotDB)
        .filter(SnapshotDB.id == snapshot_id)
        .first()
    )

    if snapshot is None:
        return None

    file_path = Path(snapshot.html_location)

    if not file_path.exists():
        return None

    return file_path.read_text(encoding="utf-8")