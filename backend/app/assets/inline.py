"""Library images carried inside an email shown in the app (task-71's
follow-up, decided with the user 2026-10-17).

The editor's preview, the send screen's "what goes out" and a recipient's
message as sent are shown in a frame with every permission withheld, so a
message gets an origin of its own and nothing in it can reach this session.
Chrome's local-network protection then refuses such a frame anything from
`localhost`, so on a development machine, or a demo run from one, every
library image showed as broken. The copy handed to these three views carries
each of the brand's library images as a `data:` address instead, and the
frame needs no network at all.

**Only the display copy.** What is rendered for sending, frozen into a
snapshot and recorded per delivery keeps its plain `/media/<token>` address
(ADR-197 point 12; ADR-183's as-sent rebuild compares against it), and a
mail client fetches it as before. An address that is not one of this brand's
library images, an https image elsewhere included, is left as it is.
"""
import base64
import re

from sqlalchemy.orm import Session

#: `src="…/media/<token>"`, `background="…"` and CSS `url(…)`: where an email
#: names an image. Any host, so a message sent under another public address
#: still finds its images.
_ADDRESS = r"https?://[^\s\"'()<>]+/media/(?P<token>[0-9A-Za-z]+)"
_ATTRIBUTE = re.compile(r"(?P<lead>\b(?:src|background)\s*=\s*)(?P<q>[\"'])" + _ADDRESS + r"(?P=q)")
_CSS = re.compile(r"(?P<lead>url\(\s*)(?P<q>[\"']?)" + _ADDRESS + r"(?P=q)(?P<tail>\s*\))")

#: A library image is at most 5 MB (the upload limit); one past this is left as an address.
_MOST = 5 * 1024 * 1024


def inline_media(db: Session, html: str | None, brand_id: int | None) -> str | None:
    """`html` with this brand's library images as `data:` addresses."""
    if not html or "/media/" not in html or brand_id is None:
        return html
    from app.assets.db_models import AssetDB
    from app.assets.service import brand_key
    from app.assets.store import get_store

    tokens = {m["token"] for m in _ATTRIBUTE.finditer(html)} | {m["token"] for m in _CSS.finditer(html)}
    if not tokens:
        return html
    store, key = get_store(), brand_key(db, brand_id)
    inlined: dict[str, str] = {}
    for asset in db.query(AssetDB).filter(AssetDB.token.in_(tokens), AssetDB.brand_id == brand_id):
        data = store.get(key, asset.token)
        if data is not None and len(data) <= _MOST:
            inlined[asset.token] = f"data:{asset.media_type};base64,{base64.b64encode(data).decode('ascii')}"

    def attribute(match: re.Match) -> str:
        found = inlined.get(match["token"])
        return f"{match['lead']}{match['q']}{found}{match['q']}" if found else match[0]

    def css(match: re.Match) -> str:
        found = inlined.get(match["token"])
        return f"{match['lead']}{match['q']}{found}{match['q']}{match['tail']}" if found else match[0]

    return _CSS.sub(css, _ATTRIBUTE.sub(attribute, html))
