from pathlib import Path

from sqlalchemy.orm import Session

from app.rendering.service import render_variant, render_variant_html
from app.snapshots.db_models import SnapshotDB
from app.snapshots.models import Snapshot
from app.campaigns.db_models import ModuleInstanceDB, DecisionResolutionDB
from app.content.service import get_latest_version_for_content


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

#Helper

def build_render_context(
    db: Session,
    variant_id: int,
    recipient_id: int | None = None,
    resolutions_by_module_id: dict[int, DecisionResolutionDB] | None = None,
) -> dict:
    from app.campaigns.service import brand_of_variant

    brand_id = brand_of_variant(db, variant_id)

    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position.asc())
        .all()
    )

    resolutions_by_module_id = resolutions_by_module_id or {}

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
            # Reuse the resolution actually used during rendering (see
            # render_variant_html's collect_resolutions) instead of
            # re-querying DecisionResolutionDB here — a second, independent
            # query could race against a new resolution being inserted
            # between the two calls, making the snapshot's HTML and its
            # recorded metadata describe different content (ADR-062).
            resolution = resolutions_by_module_id.get(module.id)

            if resolution is not None:
                module_context["content_record_id"] = resolution.content_record_id
                module_context["content_version_id"] = resolution.content_version_id
                module_context["decision_resolution_id"] = resolution.id
                module_context["resolution_status"] = "resolved"
            else:
                module_context["resolution_status"] = "no_resolution"

        elif module.content_record_id is not None:
            # The variant's own brand, resolved once above. A module whose
            # content belongs to another brand yields no version rather than
            # rendering it (ADR-172 point 5, and ADR-013's addendum: across a
            # brand boundary a reference cannot be expressed at all).
            latest_version = get_latest_version_for_content(
                db=db,
                content_record_id=module.content_record_id,
                brand_id=brand_id,
            )

            module_context["content_version_id"] = (
                latest_version.id if latest_version else None
            )
            module_context["resolution_status"] = "static_content"

        else:
            module_context["resolution_status"] = "static_module"

        context["modules"].append(module_context)

    return context

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

    artifact = render_variant(
        db=db, variant_id=variant_id, recipient_id=recipient_id, mode="send",
    )
    render_context = build_render_context(
        db=db,
        variant_id=variant_id,
        recipient_id=recipient_id,
        resolutions_by_module_id=artifact.resolutions_by_module_id,
    )

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
