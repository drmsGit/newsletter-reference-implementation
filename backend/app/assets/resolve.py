"""An image field's value, as rendering needs it (ADR-197 point 12).

A field holds `asset:<id>` (a library image of the same brand), an https
address, or nothing. Rendering needs an absolute address a mail client can
fetch, so `asset:<id>` becomes `PUBLIC_BASE_URL/media/<token>` where content
and profiles enter rendering — the live preview, the frame and every pick then
hold a plain URL, and the frame keeps it, so the as-sent rebuild stays exact
(ADR-183). An empty alt field paired with the image inherits the image's alt.

Another brand's image never resolves: it renders as no image, and saving such
a reference is refused (`check`).
"""
import re
from functools import lru_cache

from sqlalchemy.orm import Session

REFERENCE = re.compile(r"asset:(\d+)")
HTTPS = re.compile(r"https://\S+")


def public_url(token: str) -> str:
    from app.subscriptions.service import public_base_url

    return f"{public_base_url()}/media/{token}"


@lru_cache(maxsize=1)
def content_image_fields() -> dict[str, str | None]:
    """{image field: its alt field, or None} from `storage/fields.json`."""
    from app.modules.registry import field_definitions

    return {name: spec.get("alt") for name, spec in field_definitions().items() if spec.get("type") == "image"}


def asset_of(db: Session, value, brand_id: int | None):
    """The library image `value` names, in this brand; None otherwise."""
    from app.assets.db_models import AssetDB

    match = REFERENCE.fullmatch(value or "") if isinstance(value, str) else None
    if match is None:
        return None
    asset = db.get(AssetDB, int(match.group(1)))
    return asset if asset is not None and asset.brand_id == brand_id else None


def resolve_images(db: Session, values: dict, pairs: dict[str, str | None], brand_id: int | None) -> dict:
    """`values` with every `asset:<id>` in an image field made an address."""
    if not any(isinstance(values.get(name), str) and values[name].startswith("asset:") for name in pairs):
        return values
    resolved = dict(values)
    for name, alt in pairs.items():
        value = resolved.get(name)
        if not (isinstance(value, str) and value.startswith("asset:")):
            continue
        asset = asset_of(db, value, brand_id)
        resolved[name] = public_url(asset.token) if asset is not None else ""
        if asset is not None and alt and not (resolved.get(alt) or "").strip():
            resolved[alt] = asset.alt_text
    return resolved


def check(db: Session, value, brand_id: int) -> str | None:
    """Why an image field may not hold `value`, or None when it may."""
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        return "An image is a library image or an https address."
    if REFERENCE.fullmatch(value):
        return None if asset_of(db, value, brand_id) is not None else "That image is not in this brand's library."
    if HTTPS.fullmatch(value):
        return None
    return "An image is a library image or a full web address starting with https://."


def profile_image_fields() -> dict[str, str | None]:
    """{image field: its alt field, or None} from the brand-profile structure."""
    from app.brand_profiles.structure import profile_structure

    return {f.name: f.alt for f in profile_structure() if f.type == "image"}


def resolve_profile_values(db: Session, values: dict, brand_id: int | None) -> dict:
    """A profile's values with its library images made addresses."""
    return resolve_images(db, values, profile_image_fields(), brand_id)
