"""The brand's library images travel inside an email shown in the app.

Found 2026-10-17 on the Grathaus demo: the previews and the message as sent
are shown in a frame with every permission withheld, and Chrome refuses such
a frame anything from localhost, so every library image showed as broken.
The display copy carries them as data: addresses (app/assets/inline.py);
what is sent, frozen or recorded keeps the plain address.
"""
import base64
from types import SimpleNamespace

import pytest

from app.assets.db_models import AssetDB
from app.assets.inline import inline_media
from tests.test_api_guard import signed_in
from tests.test_assets import _upload, db, gif, made, store  # noqa: F401 — fixtures used by name


def _image(db, made):  # noqa: F811
    data = gif(12, 34)
    with signed_in(db) as (client, _token, csrf):
        uploaded = _upload(client, csrf, made, data=data).json()
    asset = db.get(AssetDB, uploaded["id"])
    return asset, uploaded["url"], "data:image/gif;base64," + base64.b64encode(data).decode("ascii")


def test_this_brands_library_images_become_data_addresses_and_nothing_else_does(db, made):  # noqa: F811
    asset, url, inlined = _image(db, made)
    html = (f'<img src="{url}" alt="a"><td background="{url}"></td>'
            f'<div style="background-image:url(\'{url}\')"></div>'
            '<img src="https://images.example.org/media/abc123"><img src="http://localhost:8000/media/'
            + "0" * 32 + '">')
    out = inline_media(db, html, asset.brand_id)
    assert out.count(inlined) == 3
    assert url not in out
    # Not a library image of this brand: left as it is.
    assert 'src="https://images.example.org/media/abc123"' in out
    assert "/media/" + "0" * 32 in out


def test_another_brands_image_is_never_carried_even_with_the_same_token(db, made):  # noqa: F811
    """The library is the brand's (ADR-197): even a file under the same token in
    the other brand's folder is not this brand's image."""
    import uuid

    from app.assets.store import get_store
    from app.auth.db_models import BrandDB

    asset, url, _inlined = _image(db, made)
    other = BrandDB(key=f"inline-{uuid.uuid4().hex[:8]}", name="Other brand")
    db.add(other)
    db.commit()
    try:
        get_store().put(other.key, asset.token, gif(12, 34))
        html = f'<img src="{url}">'
        assert inline_media(db, html, other.id) == html
    finally:
        db.query(BrandDB).filter(BrandDB.id == other.id).delete()
        db.commit()


def test_nothing_to_inline_is_returned_unchanged(db):  # noqa: F811
    assert inline_media(db, None, 1) is None
    assert inline_media(db, "<p>no images</p>", 1) == "<p>no images</p>"


@pytest.mark.parametrize("route", ["preview", "frame", "as_sent"])
def test_the_three_views_of_an_email_carry_its_images(db, made, monkeypatch, route):  # noqa: F811
    asset, url, inlined = _image(db, made)
    body = f'<p>Hello</p><img src="{url}" alt="a">'
    artifact = SimpleNamespace(body=body, role="html", fields=None, envelope={"subject": "S", "preheader": "P"})
    if route == "preview":
        import app.rendering.router as rendering
        monkeypatch.setattr(rendering, "render_channel_artifact", lambda **_kw: artifact)
        monkeypatch.setattr(rendering, "module_states", lambda *_a, **_kw: [])
        path, field = "/rendering/variants/1", "artifact_body"
    elif route == "frame":
        import app.delivery.service as delivery
        monkeypatch.setattr(delivery, "frame_now", lambda *_a, **_kw: {"channel": "email"})
        monkeypatch.setattr(delivery, "render_now", lambda *_a, **_kw: artifact)
        path, field = "/snapshots/variants/1/preview", "html"
    else:
        import app.delivery.router as router
        sent = {"execution_id": 1, "send_instance_id": 1, "recipient_id": 1, "channel": "email", "sent_at": None,
                "envelope": {}, "body": body, "fields": None, "modules": [], "templates_match": True,
                "hash_matches": True}
        monkeypatch.setattr(router, "reconstruct_delivery", lambda *_a, **_kw: dict(sent))
        path, field = "/delivery/executions/1/as-sent", "body"
    with signed_in(db) as (client, _token, _csrf):
        response = client.get(path)
    assert response.status_code == 200, response.text
    shown = response.json()[field]
    assert inlined in shown and url not in shown
