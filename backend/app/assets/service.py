"""The brand's image library (task-112; ADR-197).

Upload, list, replace, describe and hide. **Nothing is deleted** (point 4):
a hidden image leaves the picker and is served as before. A replacement keeps
the token, so the same address shows the new file (point 3).
"""
import secrets
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.assets import naming
from app.assets.db_models import AssetDB
from app.assets.images import FORMATS, NotAnImage, inspect
from app.assets.store import get_store

#: The upload limit (ADR-197 point 8): generous for email, sane for the disk.
MAX_BYTES = 5 * 1024 * 1024


class AssetRefused(ValueError):
    """An upload this library does not take, with a sentence saying why."""


def _check(data: bytes) -> tuple[str, int, int]:
    if not data:
        raise AssetRefused("the file is empty")
    if len(data) > MAX_BYTES:
        raise AssetRefused("images can be up to 5 MB")
    try:
        return inspect(data)
    except NotAnImage as error:
        raise AssetRefused(str(error)) from None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def brand_key(db: Session, brand_id: int) -> str:
    """The brand's permanent key (`auth.service.rename_brand` never moves it):
    the first part of a generated name and the folder its files live in."""
    from app.auth.db_models import BrandDB

    return db.query(BrandDB.key).filter(BrandDB.id == brand_id).scalar() or str(brand_id)


def upload(db: Session, *, brand_id: int, data: bytes, label: str, alt_text: str = "",
           product_id: str | None = None) -> AssetDB:
    media_type, width, height = _check(data)
    label = (label or "").strip()
    if not label:
        raise AssetRefused("give the image a name")
    today = _now().date()
    sequence = 1 + (
        db.query(func.count(AssetDB.id))
        .filter(AssetDB.brand_id == brand_id, func.date(AssetDB.created_at) == today)
        .scalar() or 0
    )
    token = secrets.token_hex(16)
    key = brand_key(db, brand_id)
    asset = AssetDB(
        brand_id=brand_id, token=token, label=label[:200], product_id=(product_id or "").strip() or None,
        sequence=sequence, media_type=media_type, size_bytes=len(data), width=width, height=height,
        alt_text=(alt_text or "").strip()[:500],
        name=naming.generate(label=label, day=today, n=sequence, width=width, height=height,
                             extension=FORMATS[media_type], product_id=product_id, brand=key),
    )
    get_store().put(key, token, data)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get(db: Session, asset_id: int, *, brand_id: int) -> AssetDB | None:
    asset = db.get(AssetDB, asset_id)
    return asset if asset is not None and asset.brand_id == brand_id else None


def find_assets(db: Session, *, brand_id: int, q: str = ""):
    """The brand's visible images, newest first; `q` matches the name or the
    alt text, part-word and any case. A query for the caller to page."""
    query = db.query(AssetDB).filter(AssetDB.brand_id == brand_id, AssetDB.hidden_at.is_(None))
    if q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.filter(or_(func.lower(AssetDB.name).like(like), func.lower(AssetDB.alt_text).like(like)))
    return query


def replace(db: Session, asset: AssetDB, data: bytes) -> AssetDB:
    """A new file for the same image (point 3): same token, so the same address."""
    media_type, width, height = _check(data)
    key = brand_key(db, asset.brand_id)
    get_store().put(key, asset.token, data)
    asset.media_type, asset.size_bytes, asset.width, asset.height = media_type, len(data), width, height
    asset.name = naming.generate(label=asset.label, day=_now().date(), n=asset.sequence, width=width,
                                 height=height, extension=FORMATS[media_type], product_id=asset.product_id,
                                 brand=key)
    db.commit()
    db.refresh(asset)
    return asset


def describe(db: Session, asset: AssetDB, alt_text: str) -> AssetDB:
    asset.alt_text = (alt_text or "").strip()[:500]
    db.commit()
    db.refresh(asset)
    return asset


def hide(db: Session, asset: AssetDB) -> AssetDB:
    """Out of the picker; still served (point 4)."""
    if asset.hidden_at is None:
        asset.hidden_at = _now()
        db.commit()
        db.refresh(asset)
    return asset


def copy_into(db: Session, source: AssetDB, *, brand_id: int) -> AssetDB:
    """Another brand's image, copied into this brand's library (decided with
    the user 2026-10-15): a new record and its own file in this brand's
    folder, so each brand's emails depend only on its own folder. A later
    replacement of the original does not reach the copy."""
    data = get_store().get(brand_key(db, source.brand_id), source.token)
    if data is None:
        raise AssetRefused("the original file is missing")
    return upload(db, brand_id=brand_id, data=data, label=source.label, alt_text=source.alt_text,
                  product_id=source.product_id)
