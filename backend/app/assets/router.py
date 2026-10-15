"""The brand's image library over the API (task-112; ADR-197).

Reading is `view`; every write is `content.manage` in the working brand (the
policy table's `/assets/` entry) and audited. Serving the files is a separate,
public router (`app.assets.public`): this one never serves bytes.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.assets import service
from app.assets.db_models import AssetDB
from app.assets.models import Asset, AssetDescribe
from app.assets.resolve import public_url
from app.audit import service as audit
from app.auth.dependencies import working_brand
from app.database import get_db
from app.pagination import Page, PageParams, page_of_query, page_params

router = APIRouter(prefix="/assets", tags=["assets"])


def to_asset(asset: AssetDB) -> Asset:
    return Asset(
        id=asset.id, name=asset.name, label=asset.label, product_id=asset.product_id,
        media_type=asset.media_type, size_bytes=asset.size_bytes, width=asset.width, height=asset.height,
        alt_text=asset.alt_text, reference=f"asset:{asset.id}", url=public_url(asset.token),
        hidden=asset.hidden_at is not None, created_at=asset.created_at, updated_at=asset.updated_at,
    )


def _found(db: Session, asset_id: int, brand_id: int) -> AssetDB:
    asset = service.get(db, asset_id, brand_id=brand_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return asset


async def _read(file: UploadFile) -> bytes:
    data = await file.read(service.MAX_BYTES + 1)
    if len(data) > service.MAX_BYTES:
        raise HTTPException(status_code=413, detail="images can be up to 5 MB")
    return data


@router.get("/", response_model=Page[Asset], summary="The brand's images, newest first")
def list_assets(
    q: str = Query("", description="Find by name or alt text (part, any case)."),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    query = service.find_assets(db, brand_id=brand_id, q=q)
    return page_of_query(query, params, AssetDB.created_at.desc(), AssetDB.id.desc(), convert=to_asset)


@router.get("/{asset_id}", response_model=Asset)
def get_asset(asset_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    return to_asset(_found(db, asset_id, brand_id))


@router.post("/", response_model=Asset, status_code=201,
             summary="Upload an image: JPEG, PNG, GIF or WebP, up to 5 MB")
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(..., description="What it shows; the generated name is built from it."),
    alt_text: str = Form(""),
    product_id: str | None = Form(None),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    data = await _read(file)
    try:
        asset = service.upload(db, brand_id=brand_id, data=data, label=name, alt_text=alt_text,
                               product_id=product_id)
    except service.AssetRefused as error:
        raise HTTPException(status_code=422, detail=str(error))
    audit.record_from_request(request, db, audit.ASSET_UPLOADED, subject_type="asset", subject_id=asset.id,
                              brand_id=brand_id, detail={"name": asset.name})
    return to_asset(asset)


@router.post("/{asset_id}/replace", response_model=Asset,
             summary="A new file for the same image: same address, so sent emails show it too")
async def replace_asset(
    asset_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    asset = _found(db, asset_id, brand_id)
    data = await _read(file)
    try:
        asset = service.replace(db, asset, data)
    except service.AssetRefused as error:
        raise HTTPException(status_code=422, detail=str(error))
    audit.record_from_request(request, db, audit.ASSET_REPLACED, subject_type="asset", subject_id=asset.id,
                              brand_id=brand_id, detail={"name": asset.name})
    return to_asset(asset)


@router.put("/{asset_id}/alt", response_model=Asset, summary="Change an image's alt text")
def describe_asset(
    asset_id: int,
    payload: AssetDescribe,
    request: Request,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    asset = service.describe(db, _found(db, asset_id, brand_id), payload.alt_text)
    audit.record_from_request(request, db, audit.ASSET_DESCRIBED, subject_type="asset", subject_id=asset.id,
                              brand_id=brand_id, detail={"name": asset.name})
    return to_asset(asset)


@router.post("/{asset_id}/hide", response_model=Asset,
             summary="Take an image out of the picker; it is still served (ADR-197 point 4)")
def hide_asset(asset_id: int, request: Request, db: Session = Depends(get_db),
               brand_id: int = Depends(working_brand)):
    asset = service.hide(db, _found(db, asset_id, brand_id))
    audit.record_from_request(request, db, audit.ASSET_HIDDEN, subject_type="asset", subject_id=asset.id,
                              brand_id=brand_id, detail={"name": asset.name})
    return to_asset(asset)
