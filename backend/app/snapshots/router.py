from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
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
):
    return create_snapshot_for_variant(
        db=db,
        variant_id=variant_id,
        recipient_id=recipient_id,
    )


@router.get("/variants/{variant_id}", response_model=list[Snapshot])
def get_variant_snapshots(
    variant_id: int,
    db: Session = Depends(get_db),
):
    return list_snapshots_for_variant(
        db=db,
        variant_id=variant_id,
    )


@router.get("/{snapshot_id}/html", response_class=HTMLResponse)
def get_snapshot_html_file(
    snapshot_id: int,
    db: Session = Depends(get_db),
):
    html = get_snapshot_html(
        db=db,
        snapshot_id=snapshot_id,
    )

    if html is None:
        raise HTTPException(status_code=404, detail="Snapshot HTML not found")

    return HTMLResponse(content=html)