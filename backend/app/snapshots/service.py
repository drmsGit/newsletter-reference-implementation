from sqlalchemy.orm import Session

from app.snapshots.db_models import SnapshotDB
from app.snapshots.models import Snapshot


def to_snapshot(record: SnapshotDB) -> Snapshot:
    return Snapshot(
        id=record.id,
        variant_id=record.variant_id,
        recipient_id=record.recipient_id,
        artifact_storage_type=record.artifact_storage_type,
        artifact_location=record.artifact_location,
        artifact_size=record.artifact_size,
        created_at=record.created_at,
        render_context=record.render_context,
    )


#: What `artifact_location` says for an artifact that is not a file. The column is
#: NOT NULL and named for HTML because it predates channels; renaming it is
#: part of the open snapshot-storage question, not of this change.
INLINE_LOCATION = "inline:render_context"


def _snapshot_in_brand(db: Session, snapshot_id: int, brand_id: int):
    """A snapshot, if its variant's campaign belongs to this brand.

    Three hops — `snapshot -> variant -> campaign -> brand` — walked in the
    selecting query (ADR-172 point 5). Snapshots carry no brand column and do
    not need one.
    """
    from app.campaigns.db_models import CampaignDB, VariantDB

    return (
        db.query(SnapshotDB)
        .join(VariantDB, VariantDB.id == SnapshotDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(SnapshotDB.id == snapshot_id, CampaignDB.brand_id == brand_id)
        .first()
    )


def create_snapshot_for_variant(
    db: Session, variant_id: int, recipient_id: int | None = None, *, brand_id: int
) -> Snapshot:
    """Freeze a variant for approval and planning: its frame (ADR-183).

    The frame is the composition with its values copied in — what the send
    renders from and what was approved. It lives in the row for every channel;
    nothing is written to disk. A preview is the frame laid out on demand
    (`get_snapshot_html`, `get_snapshot_artifact`).

    History, kept because the reasoning still holds: push was the first
    channel stored in the row (2026-09-17), and the email HTML file it sat
    beside was held back from being hardened (task-46, 2026-09-14) because the
    project leaned toward exactly this. ADR-183 settled the storage question.
    """
    # The variant is resolved within the brand before anything is rendered or
    # written (ADR-172 point 5). A snapshot freezes one brand's composition; a
    # caller in another brand has no business producing one.
    from app.campaigns.service import get_variant

    if get_variant(db, variant_id, brand_id=brand_id) is None:
        raise ValueError(f"variant {variant_id} does not exist")

    # **The frame is the snapshot** (ADR-183): the composition frozen with its
    # values, which the send renders from. The artifact below is that frame
    # laid out for this recipient (or nobody), so the preview is what the frame
    # produces rather than a second, live render that could disagree with it.
    from app.rendering.frame import build_frame, render_frame

    render_context = {**build_frame(db, variant_id), "recipient_id": recipient_id}
    artifact, _picks = render_frame(db, render_context, recipient_id=recipient_id)

    # **One storage shape, and no file** (ADR-183 point 5). The frame is the
    # snapshot; a preview is rendered from it on demand. Until 2026-10-02 email
    # wrote an HTML file — committed as "pending" before the file existed
    # (task-46) — that the send never read, and push kept a copy of its payload
    # in the row. Both were copies of something the frame now produces.
    snapshot = SnapshotDB(
        variant_id=variant_id,
        recipient_id=recipient_id,
        artifact_storage_type="inline",
        artifact_location=INLINE_LOCATION,
        artifact_size=artifact.size_bytes(),
        render_context=render_context,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return to_snapshot(snapshot)


def list_snapshots_for_variant(
    db: Session, variant_id: int, *, brand_id: int
) -> list[Snapshot]:
    from app.campaigns.db_models import CampaignDB, VariantDB

    records = (
        db.query(SnapshotDB)
        .join(VariantDB, VariantDB.id == SnapshotDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(
            SnapshotDB.variant_id == variant_id,
            CampaignDB.brand_id == brand_id,
        )
        .order_by(SnapshotDB.created_at.desc())
        .all()
    )

    return [to_snapshot(record) for record in records]


def _render_snapshot(db: Session, snapshot: SnapshotDB):
    """The snapshot's frame laid out — for its recipient, or nobody. None for a
    snapshot made before ADR-183, which has no frame to render."""
    from app.rendering.frame import is_frame, render_frame

    if not is_frame(snapshot.render_context):
        return None
    artifact, _ = render_frame(db, snapshot.render_context, recipient_id=snapshot.recipient_id)
    return artifact


def get_snapshot_html(db: Session, snapshot_id: int, *, brand_id: int) -> str | None:
    """The snapshot as an email document, rendered from its frame. None when it
    is not in this brand, has no frame, or is not an email (a push payload)."""
    snapshot = _snapshot_in_brand(db, snapshot_id, brand_id)
    if snapshot is None:
        return None
    artifact = _render_snapshot(db, snapshot)
    return artifact.body if artifact is not None else None


def get_snapshot_artifact(db: Session, snapshot_id: int, *, brand_id: int) -> dict | None:
    """What this snapshot froze, laid out: `{"role": "html", "body": ...}` for
    email, `{"role": "payload", "fields": {...}}` for push. Same call for every
    channel, because the frame is the same shape for every channel."""
    snapshot = _snapshot_in_brand(db, snapshot_id, brand_id)
    if snapshot is None:
        return None
    artifact = _render_snapshot(db, snapshot)
    if artifact is None:
        return None
    result = {"role": artifact.role, "media_type": artifact.media_type}
    if artifact.body is not None:
        result["body"] = artifact.body
    else:
        result["fields"] = artifact.fields or {}
    return result
