from pathlib import Path

from sqlalchemy.orm import Session

from app.rendering.service import render_variant_html
from app.snapshots.db_models import SnapshotDB
from app.snapshots.models import Snapshot
from app.campaigns.db_models import ModuleInstanceDB, DecisionResolutionDB
from app.content.service import get_latest_version_for_content


SNAPSHOT_STORAGE_DIR = Path("../storage/snapshots")


def to_snapshot(record: SnapshotDB) -> Snapshot:
    return Snapshot(
        id=record.id,
        variant_id=record.variant_id,
        recipient_id=record.recipient_id,
        html_storage_type=record.html_storage_type,
        html_location=record.html_location,
        html_size=record.html_size,
        created_at=record.created_at,
        render_context=record.render_context,
    )

#Helper

def build_render_context(
    db: Session,
    variant_id: int,
    recipient_id: int | None = None,
) -> dict:
    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position.asc())
        .all()
    )

    context = {
        "variant_id": variant_id,
        "recipient_id": recipient_id,
        "modules": [],
    }

    for module in modules:
        module_context = {
            "module_id": module.id,
            "module_type": module.module_type,
            "position": module.position,
            "content_record_id": module.content_record_id,
            "content_version_id": None,
            "decision_slot_id": module.decision_slot_id,
            "decision_resolution_id": None,
            "resolution_status": None,
        }

        if module.decision_slot_id is not None and recipient_id is not None:
            resolution = (
                db.query(DecisionResolutionDB)
                .filter(
                    DecisionResolutionDB.decision_slot_id == module.decision_slot_id,
                    DecisionResolutionDB.recipient_id == recipient_id,
                )
                .order_by(DecisionResolutionDB.created_at.desc())
                .first()
            )

            if resolution is not None:
                module_context["content_record_id"] = resolution.content_record_id
                module_context["content_version_id"] = resolution.content_version_id
                module_context["decision_resolution_id"] = resolution.id
                module_context["resolution_status"] = "resolved"
            else:
                module_context["resolution_status"] = "no_resolution"

        elif module.content_record_id is not None:
            latest_version = get_latest_version_for_content(
                db=db,
                content_record_id=module.content_record_id,
            )

            module_context["content_version_id"] = (
                latest_version.id if latest_version else None
            )
            module_context["resolution_status"] = "static_content"

        else:
            module_context["resolution_status"] = "static_module"

        context["modules"].append(module_context)

    return context

def create_snapshot_for_variant(db: Session, variant_id: int, recipient_id: int | None = None) -> Snapshot:
    render_context = {
        "variant_id": variant_id,
        "recipient_id": recipient_id,
    }
    
    html = render_variant_html(db=db, variant_id=variant_id, recipient_id=recipient_id,)
    render_context = build_render_context(
        db=db,
        variant_id=variant_id,
        recipient_id=recipient_id,
    )

    SNAPSHOT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = SnapshotDB(
        variant_id=variant_id,
        recipient_id=recipient_id,
        html_storage_type="file",
        html_location="pending",
        html_size=len(html.encode("utf-8")),
        render_context=render_context,
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    recipient_part = (
        f"recipient-{recipient_id}"
        if recipient_id is not None
        else "global"
    )

    file_name = f"variant-{variant_id}-{recipient_part}-snapshot-{snapshot.id}.html"
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