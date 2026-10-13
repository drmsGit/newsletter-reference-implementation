from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import working_brand
from app.database import get_db
from app.rendering.service import UnpublishedContentError
from app.snapshots.models import Snapshot, VariantFramePreview
from app.snapshots.service import (
    create_snapshot_for_variant,
    get_snapshot_html,
    list_snapshots_for_variant,
)


router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.post("/variants/{variant_id}", response_model=Snapshot)
def create_variant_snapshot(
    variant_id: int,
    recipient_id: int | None = None,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        return create_snapshot_for_variant(
            db=db,
            variant_id=variant_id,
            recipient_id=recipient_id,
            brand_id=brand_id,
        )
    except UnpublishedContentError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        # A variant that does not exist, or not in this brand (task-67).
        # Answered 500 before: the service raises a bare ValueError.
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/variants/{variant_id}/preview",
    response_model=VariantFramePreview,
    summary="What the variant would send if frozen now",
    description=(
        "The frame planning would freeze now, laid out — built in memory and never stored "
        "(ADR-183 addendum 2026-10-13). Email returns the HTML; push its fields. As `recipient_id` "
        "would get it, or nobody in particular. 409 for unpublished content."
    ),
)
def preview_variant_frame(
    variant_id: int,
    recipient_id: int | None = None,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.delivery.service import frame_now, render_now

    try:
        frame = frame_now(db, variant_id, brand_id=brand_id)
        if frame is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        artifact = render_now(db, frame, recipient_id)
    except UnpublishedContentError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return VariantFramePreview(
        channel=frame["channel"], subject=artifact.envelope.get("subject"),
        preheader=artifact.envelope.get("preheader"), html=artifact.body, fields=artifact.fields or None,
    )


@router.get("/variants/{variant_id}", response_model=list[Snapshot])
def get_variant_snapshots(
    variant_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return list_snapshots_for_variant(
        db=db,
        variant_id=variant_id,
        brand_id=brand_id,
    )


@router.get("/{snapshot_id}/html", response_class=HTMLResponse)
def get_snapshot_html_file(
    snapshot_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    html = get_snapshot_html(
        db=db,
        snapshot_id=snapshot_id,
        brand_id=brand_id,
    )

    if html is None:
        # Distinguish "this snapshot has no HTML by nature" from "the file is
        # missing". A push snapshot stores a field payload in its row
        # (2026-09-17), so "not found" was true of the HTML and misleading
        # about the snapshot, which is present and complete.
        from app.snapshots.db_models import SnapshotDB

        from app.rendering.frame import is_frame

        snapshot = db.query(SnapshotDB).filter(SnapshotDB.id == snapshot_id).first()
        context = snapshot.render_context if snapshot is not None else None
        if snapshot is not None and not is_frame(context):
            raise HTTPException(
                status_code=404,
                detail=(
                    "This snapshot was made before snapshots froze their content "
                    "(ADR-183) and has nothing to render. Take a new snapshot."
                ),
            )
        if snapshot is not None and context.get("channel") != "email":
            raise HTTPException(
                status_code=404,
                detail=(
                    "This snapshot is not an HTML document — it is a field "
                    "payload. Read it from the snapshot's artifact."
                ),
            )
        raise HTTPException(status_code=404, detail="Snapshot HTML not found")

    return HTMLResponse(content=html)