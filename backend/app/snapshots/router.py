from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.snapshots.models import Snapshot
from app.snapshots.service import create_snapshot_for_variant, list_snapshots_for_variant


router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.post("/variants/{variant_id}", response_model=Snapshot)
def create_variant_snapshot(
    variant_id: int,
    db: Session = Depends(get_db),
):
    return create_snapshot_for_variant(
        db=db,
        variant_id=variant_id,
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