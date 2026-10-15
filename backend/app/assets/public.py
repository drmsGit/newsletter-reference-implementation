"""Serving library images to whoever asks (ADR-197 point 3).

**The one thing in the platform that must serve anonymously**: a mail client
fetches an image days later with no session. The random token in the path is
the protection (point 11) — it protects everything except an image that was
mailed, which was public the moment it was sent. Hidden images are served too:
an email in an inbox still shows them (point 4).
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.assets.db_models import AssetDB
from app.assets.store import get_store
from app.database import get_db

router = APIRouter(include_in_schema=False)


@router.get("/media/{token}")
def serve(token: str, db: Session = Depends(get_db)):
    asset = db.query(AssetDB).filter(AssetDB.token == token).first() if token.isalnum() else None
    from app.assets.service import brand_key

    data = get_store().get(brand_key(db, asset.brand_id), asset.token) if asset is not None else None
    if data is None:
        raise HTTPException(status_code=404, detail="Not found")
    # A replacement keeps the address (point 3), so a long cache would hide it.
    return Response(content=data, media_type=asset.media_type,
                    headers={"Cache-Control": "public, max-age=3600",
                             "X-Content-Type-Options": "nosniff"})
