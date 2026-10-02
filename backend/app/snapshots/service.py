from pathlib import Path

from sqlalchemy.orm import Session

from app.snapshots.db_models import SnapshotDB
from app.snapshots.models import Snapshot


SNAPSHOT_STORAGE_DIR = (Path(__file__).parent.parent.parent.parent / "storage" / "snapshots").resolve()


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
    """Freeze a variant for approval and planning.

    **Two storage shapes, and the split is deliberate rather than tidy.** Email
    keeps writing an HTML file, exactly as before. A non-HTML artifact — push,
    today — is stored *in the row*, under `render_context["artifact"]`, with
    `artifact_storage_type="inline"` and no file at all.

    Decided 2026-09-17 (user). Writing a push payload to a `.json` beside the
    `.html` files was the smaller diff and was rejected: it would harden the
    artifact the project has a recorded lean away from — the same reasoning
    that put the snapshot-atomicity bug on hold on 2026-09-14 — and leave
    columns named `html_*` holding a push payload, which is a lie the next
    reader has to decode.

    **This does not decide the snapshot-storage question**, which is still an
    open Needs-ADR item covering approval-snapshot vs per-delivery package, the
    medium, and whether per-recipient renders are persisted at all. It makes
    push the first channel whose artifact lives in a table, which is the
    direction that item is already leaning, and leaves email where it is. Two
    shapes coexisting is visible rather than hidden, and that is the point.
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

    if artifact.body is None:
        # Structured artifact: it IS the render context's business, so it goes
        # in beside the per-module resolutions rather than to disk.
        render_context = {
            **(render_context or {}),
            "artifact": {
                "role": artifact.role,
                "media_type": artifact.media_type,
                "fields": artifact.fields or {},
            },
        }
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

    SNAPSHOT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = SnapshotDB(
        variant_id=variant_id,
        recipient_id=recipient_id,
        artifact_storage_type="file",
        artifact_location="pending",
        artifact_size=artifact.size_bytes(),
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
    file_path.write_text(artifact.body, encoding="utf-8")

    snapshot.artifact_location = str(file_path)
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


def get_snapshot_html(db: Session, snapshot_id: int, *, brand_id: int) -> str | None:
    snapshot = _snapshot_in_brand(db, snapshot_id, brand_id)

    if snapshot is None:
        return None

    if snapshot.artifact_storage_type == "inline":
        # Not a file, and not a failure either. Returning None here would be
        # indistinguishable from "the file went missing", which is the state
        # this function was written to report — so the caller is told plainly
        # via `get_snapshot_artifact` instead.
        return None

    file_path = Path(snapshot.artifact_location)

    if not file_path.exists():
        return None

    return file_path.read_text(encoding="utf-8")


def get_snapshot_artifact(db: Session, snapshot_id: int, *, brand_id: int) -> dict | None:
    """What this snapshot froze, whatever shape it is in.

    Answers for both storage shapes so a caller does not have to know which one
    a channel uses: `{"role": "html", "body": ...}` for email,
    `{"role": "payload", "fields": {...}}` for push.
    """
    snapshot = _snapshot_in_brand(db, snapshot_id, brand_id)
    if snapshot is None:
        return None

    if snapshot.artifact_storage_type == "inline":
        stored = (snapshot.render_context or {}).get("artifact")
        return dict(stored) if stored else None

    html = get_snapshot_html(db, snapshot_id, brand_id=brand_id)
    if html is None:
        return None
    return {"role": "html", "media_type": "text/html", "body": html}
