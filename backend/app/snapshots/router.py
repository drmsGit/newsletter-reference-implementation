from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import working_brand
from app.database import get_db
from app.rendering.service import UnpublishedContentError
from app.snapshots.models import Snapshot
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

        snapshot = db.query(SnapshotDB).filter(SnapshotDB.id == snapshot_id).first()
        if snapshot is not None and snapshot.html_storage_type == "inline":
            raise HTTPException(
                status_code=404,
                detail=(
                    "This snapshot is not an HTML document — its artifact is a "
                    "field payload stored in the snapshot row. Read it from the "
                    "snapshot itself."
                ),
            )
        raise HTTPException(status_code=404, detail="Snapshot HTML not found")

    return HTMLResponse(content=html)