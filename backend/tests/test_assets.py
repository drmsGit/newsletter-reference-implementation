"""A brand's image library (task-112; ADR-197, ADR-177 and ADR-194 addenda
of 2026-10-15).

Decided with the user (2026-09-27 and 2026-10-15): images are records a field
refers to; alt text on the image, overridable where used; replaced in place;
served from an unguessable path without a session; never deleted, only hidden;
search only, over generated names; content images and brand logos; a field
holds a library image or an https address; JPEG, PNG, GIF, WebP up to 5 MB;
the name template is a setup file.
"""
import struct
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.assets import images, naming, resolve
from app.assets.db_models import AssetDB
from app.audit.db_models import AuditEventDB
from app.auth.permissions import VIEW
from app.content.db_models import ContentRecordDB
from app.database import SessionLocal
from main import app
from tests.machine import machine
from tests.test_api_guard import signed_in

anonymous = TestClient(app, raise_server_exceptions=False)


def png(width=120, height=80) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height) + b"\x08\x06" + b"\x00" * 64


def gif(width=10, height=20) -> bytes:
    return b"GIF89a" + struct.pack("<HH", width, height) + b"\x00" * 16


def jpeg(width=640, height=480) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    sof = b"\xff\xc0" + struct.pack(">H", 17) + b"\x08" + struct.pack(">HH", height, width) + b"\x03" + b"\x00" * 9
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


def webp(width=300, height=200) -> bytes:
    body = b"VP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00" + (width - 1).to_bytes(3, "little") \
        + (height - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP" + body


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path / "assets"))
    return tmp_path / "assets"


@pytest.fixture
def made(db):
    """Asset and content ids made through the API, removed afterwards."""
    ids = {"assets": [], "records": []}
    yield ids
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "asset",
                                  AuditEventDB.subject_id.in_(ids["assets"])).delete(synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(ids["records"])).delete(synchronize_session=False)
    db.query(AssetDB).filter(AssetDB.id.in_(ids["assets"])).delete(synchronize_session=False)
    db.commit()


def _upload(client, csrf, made, data=None, name="Summer sale", alt="A beach at noon", **extra):
    response = client.post("/assets/", files={"file": ("whatever.bin", png() if data is None else data, "application/octet-stream")},
                           data={"name": name, "alt_text": alt, **extra}, headers={"X-CSRF-Token": csrf})
    if response.status_code == 201:
        made["assets"].append(response.json()["id"])
    return response


# --- what a file is -------------------------------------------------------------------------

@pytest.mark.parametrize("data, expected", [
    (png(120, 80), ("image/png", 120, 80)),
    (gif(10, 20), ("image/gif", 10, 20)),
    (jpeg(640, 480), ("image/jpeg", 640, 480)),
    (webp(300, 200), ("image/webp", 300, 200)),
])
def test_the_type_and_size_come_from_the_bytes(data, expected):
    assert images.inspect(data) == expected


@pytest.mark.parametrize("data", [b"<svg xmlns='http://www.w3.org/2000/svg'/>", b"%PDF-1.4", b"just text"])
def test_anything_else_is_not_an_image(data):
    with pytest.raises(images.NotAnImage):
        images.inspect(data)


def test_names_are_plain_words():
    assert naming.clean("Sommer-Aktion: Größe & Preis!") == "sommer-aktion-groesse-and-preis"
    assert naming.generate(label="Summer sale", day=date(2026, 10, 15), n=3, width=1200, height=600,
                           extension="jpg", brand="acme") == "acme-20261015-3-1200x600-summer-sale.jpg"


# --- the library over the API ---------------------------------------------------------------------

def test_an_upload_is_named_from_the_template_and_served_by_token(db, made):
    with signed_in(db) as (client, _token, csrf):
        first = _upload(client, csrf, made)
        second = _upload(client, csrf, made, data=jpeg(640, 480), name="Second one")
    assert first.status_code == 201, first.text
    body = first.json()
    today = date.today().strftime("%Y%m%d")
    brand = db.get(AssetDB, body["id"]).brand_id
    from app.auth.db_models import BrandDB

    key = db.get(BrandDB, brand).key
    assert body["name"].startswith(f"{naming.clean(key)}-{today}-") and body["name"].endswith("-120x80-summer-sale.png")
    assert body["reference"] == f"asset:{body['id']}"
    token = body["url"].rsplit("/media/", 1)[1]
    assert len(token) >= 32 and token not in body["name"]
    def running(name):
        return int(name[len(naming.clean(key)) + 1:].split("-")[1])

    n_first, n_second = running(body["name"]), running(second.json()["name"])
    assert n_second == n_first + 1 and second.json()["name"].endswith("-640x480-second-one.jpg")


@pytest.mark.parametrize("data, reason", [
    (b"<svg/>", "JPEG, PNG, GIF and WebP"),
    (b"", "empty"),
])
def test_what_is_not_an_email_image_is_refused(db, made, data, reason):
    with signed_in(db) as (client, _token, csrf):
        response = _upload(client, csrf, made, data=data)
    assert response.status_code == 422 and reason in response.json()["detail"]


def test_more_than_5_mb_is_refused(db, made):
    with signed_in(db) as (client, _token, csrf):
        response = _upload(client, csrf, made, data=png() + b"\x00" * (5 * 1024 * 1024))
    assert response.status_code == 413


def test_the_file_is_served_to_anyone_who_has_the_address(db, made, store):
    data = gif()
    with signed_in(db) as (client, _token, csrf):
        uploaded = _upload(client, csrf, made, data=data).json()
    url = uploaded["url"]
    from app.auth.db_models import BrandDB

    key = db.get(BrandDB, db.get(AssetDB, uploaded["id"]).brand_id).key
    assert (store / key / url.rsplit("/media/", 1)[1]).is_file(), "a folder per brand"
    response = anonymous.get("/media/" + url.rsplit("/media/", 1)[1])
    assert response.status_code == 200 and response.content == data
    assert response.headers["content-type"] == "image/gif"
    assert anonymous.get("/media/" + "0" * 32).status_code == 404


def test_hiding_takes_it_out_of_the_picker_and_it_is_still_served(db, made):
    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made, name=f"hide-{uuid.uuid4().hex[:6]}").json()
        assert client.post(f"/assets/{asset['id']}/hide", headers={"X-CSRF-Token": csrf}).status_code == 200
        listed = [a["id"] for a in client.get("/assets/", params={"q": asset["name"]}).json()["items"]]
    assert asset["id"] not in listed
    assert anonymous.get("/media/" + asset["url"].rsplit("/media/", 1)[1]).status_code == 200


def test_search_finds_by_name_or_alt(db, made):
    word = uuid.uuid4().hex[:8]
    with signed_in(db) as (client, _token, csrf):
        by_name = _upload(client, csrf, made, name=f"Lighthouse {word}").json()
        by_alt = _upload(client, csrf, made, name="Other", alt=f"a {word} at dusk").json()
        _upload(client, csrf, made, name="Unrelated")
        found = {a["id"] for a in client.get("/assets/", params={"q": word}).json()["items"]}
    assert found == {by_name["id"], by_alt["id"]}


def test_a_replacement_keeps_the_address(db, made):
    with signed_in(db) as (client, _token, csrf):
        before = _upload(client, csrf, made, data=png(100, 100)).json()
        after = client.post(f"/assets/{before['id']}/replace",
                            files={"file": ("x", jpeg(800, 400), "application/octet-stream")},
                            headers={"X-CSRF-Token": csrf}).json()
    assert after["url"] == before["url"]
    assert (after["width"], after["height"], after["media_type"]) == (800, 400, "image/jpeg")
    assert after["name"].endswith("-800x400-summer-sale.jpg")
    assert anonymous.get("/media/" + after["url"].rsplit("/media/", 1)[1]).content == jpeg(800, 400)


def test_the_alt_text_can_be_changed(db, made):
    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made).json()
        changed = client.put(f"/assets/{asset['id']}/alt", json={"alt_text": "Sunset over the dunes"},
                             headers={"X-CSRF-Token": csrf}).json()
    assert changed["alt_text"] == "Sunset over the dunes"


def test_writes_are_audited(db, made):
    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made).json()
    entry = db.query(AuditEventDB).filter(AuditEventDB.action == "asset.uploaded",
                                          AuditEventDB.subject_id == asset["id"]).one()
    assert entry.detail["name"] == asset["name"]


def test_another_brands_image_is_not_found(db, foreign_brand, made):
    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made).json()
    row = db.get(AssetDB, asset["id"])
    row.brand_id = foreign_brand.id
    db.commit()
    with signed_in(db) as (client, _token, csrf):
        assert client.get(f"/assets/{asset['id']}").status_code == 404
        assert asset["id"] not in [a["id"] for a in client.get("/assets/").json()["items"]]


def test_uploading_needs_the_right_to_make_content():
    with machine([VIEW]) as headers:
        response = anonymous.post("/assets/", files={"file": ("x", png(), "image/png")},
                                  data={"name": "x"}, headers=headers)
    assert response.status_code == 403


# --- an image field refers to it ---------------------------------------------------------------------

def test_image_fields_are_declared_with_their_alt():
    assert resolve.content_image_fields() == {"image_url": "image_alt", "push_image_url": None}
    assert resolve.profile_image_fields() == {"logo": "logo_alt"}


def _record(db, made, brand_id, content):
    from app.content.service import create_content

    record = create_content(db, title=f"img-{uuid.uuid4().hex[:6]}", content=content, brand_id=brand_id)
    made["records"].append(record.id)
    return record


def test_rendering_turns_a_reference_into_an_address_and_inherits_the_alt(db, made, default_brand):
    from app.rendering.service import resolve_renderable_content

    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made, alt="A beach at noon").json()
    plain = _record(db, made, default_brand.id, {"image_url": asset["reference"], "image_alt": ""})
    typed = _record(db, made, default_brand.id, {"image_url": asset["reference"], "image_alt": "Our shop"})
    shown = resolve_renderable_content(db, plain.id)
    assert shown["image_url"] == asset["url"] and shown["image_url"].startswith("http")
    assert shown["image_alt"] == "A beach at noon"
    assert resolve_renderable_content(db, typed.id)["image_alt"] == "Our shop", "the usage's own alt wins"


def test_an_outside_address_is_left_as_it_is(db, made, default_brand):
    from app.rendering.service import resolve_renderable_content

    record = _record(db, made, default_brand.id, {"image_url": "https://cdn.example.org/a.jpg"})
    assert resolve_renderable_content(db, record.id)["image_url"] == "https://cdn.example.org/a.jpg"


@pytest.mark.parametrize("value, ok", [
    ("https://cdn.example.org/a.jpg", True),
    ("http://cdn.example.org/a.jpg", False),
    ("/static/img/demo-1.jpg", False),
    ("asset:987654321", False),
])
def test_saving_an_image_field_checks_its_value(db, made, default_brand, value, ok):
    record = _record(db, made, default_brand.id, {})
    with signed_in(db) as (client, _token, csrf):
        response = client.patch(f"/content/{record.id}", json={"content": {"image_url": value}, "groups": ["email"]},
                                headers={"X-CSRF-Token": csrf})
    assert (response.status_code == 200) is ok, response.text
    if not ok:
        assert response.status_code == 422 and "image_url" in response.json()["detail"]


def test_a_stored_value_from_before_does_not_block_other_edits(db, made, default_brand):
    record = _record(db, made, default_brand.id, {})
    row = db.get(ContentRecordDB, record.id)
    row.content = {"image_url": "/static/img/demo-1.jpg", "headline_medium": "Old"}
    db.commit()
    with signed_in(db) as (client, _token, csrf):
        response = client.patch(f"/content/{record.id}", json={"content": {"headline_medium": "New"}, "groups": ["email"]},
                                headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200, response.text


def test_another_brands_image_cannot_be_used_and_renders_as_none(db, default_brand, foreign_brand, made):
    from app.rendering.service import resolve_renderable_content

    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made).json()
    row = db.get(AssetDB, asset["id"])
    row.brand_id = foreign_brand.id
    db.commit()
    record = _record(db, made, default_brand.id, {})
    with signed_in(db) as (client, _token, csrf):
        response = client.patch(f"/content/{record.id}", json={"content": {"image_url": asset["reference"]},
                                                               "groups": ["email"]}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 422
    stored = db.get(ContentRecordDB, record.id)
    stored.content = {"image_url": asset["reference"]}
    db.commit()
    assert resolve_renderable_content(db, record.id)["image_url"] == ""


def test_a_brand_logo_may_be_a_library_image(db, made, default_brand):
    from app.brand_profiles.service import ProfileInvalid, clean_values

    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made, alt="Shop logo").json()
    assert clean_values({"logo": asset["reference"]}, db=db, brand_id=default_brand.id) == {"logo": asset["reference"]}
    with pytest.raises(ProfileInvalid):
        clean_values({"logo": "asset:987654321"}, db=db, brand_id=default_brand.id)
    assert resolve.resolve_profile_values(db, {"logo": asset["reference"]}, default_brand.id) == {
        "logo": asset["url"], "logo_alt": "Shop logo"}


def test_the_service_refuses_more_than_5_mb_too(db, default_brand):
    from app.assets import service

    with pytest.raises(service.AssetRefused):
        service.upload(db, brand_id=default_brand.id, data=png() + b"\x00" * (5 * 1024 * 1024), label="big")


@pytest.fixture
def logo_profile(db, made, default_brand):
    """The default brand's default profile with a library logo; restored after."""
    from app.brand_profiles.service import ensure_default_profile

    with signed_in(db) as (client, _token, csrf):
        asset = _upload(client, csrf, made, alt="Shop logo").json()
    profile = ensure_default_profile(db, default_brand.id)
    before = dict(profile.field_values or {})
    profile.field_values = {**before, "logo": asset["reference"], "logo_alt": ""}
    db.commit()
    yield asset
    db.rollback()
    profile.field_values = before
    db.commit()


def test_the_live_render_frame_and_session_show_the_library_logo(db, logo_profile, default_brand):
    from app.brand_profiles.theme import live_theme
    from app.campaigns.db_models import CampaignDB, VariantDB
    from app.rendering.frame import build_frame

    campaign = CampaignDB(name=f"logo-{uuid.uuid4().hex[:6]}", status="draft", brand_id=default_brand.id)
    db.add(campaign)
    db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="V", status="draft")
    db.add(variant)
    db.commit()
    try:
        assert live_theme(db, variant)["values"]["logo"] == logo_profile["url"]
        frozen = build_frame(db, variant.id)["brand_profile"]["values"]
        assert (frozen["logo"], frozen["logo_alt"]) == (logo_profile["url"], "Shop logo"), "the frame keeps the address"
        with signed_in(db) as (client, _token, _csrf):
            brand = client.get("/auth/session").json()["brand"]
        assert brand["logo"] == logo_profile["url"]
    finally:
        db.rollback()
        db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
        db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
        db.commit()


# --- across brands (decided with the user 2026-10-15) --------------------------------------------

@pytest.fixture
def foreign_image(db, foreign_brand, made, store):
    """An image in the other brand's library, with its file in that brand's folder."""
    from app.assets import service

    asset = service.upload(db, brand_id=foreign_brand.id, data=gif(30, 40), label="Their logo",
                           alt_text="Their alt")
    made["assets"].append(asset.id)
    return asset


def test_a_person_with_both_brands_sees_and_copies_the_others_images(db, foreign_image, foreign_brand, made,
                                                                   two_brand_person):
    from app.auth.db_models import BrandDB

    client, csrf = two_brand_person
    listed = client.get("/assets/", params={"brand": foreign_brand.id}).json()["items"]
    assert foreign_image.id in [a["id"] for a in listed]
    response = client.post(f"/assets/{foreign_image.id}/copy", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 201, response.text
    copy = response.json()
    made["assets"].append(copy["id"])
    working = db.get(AssetDB, copy["id"]).brand_id
    assert working != foreign_brand.id and copy["id"] != foreign_image.id
    assert (copy["label"], copy["alt_text"], copy["width"]) == ("Their logo", "Their alt", 30)
    assert copy["name"].startswith(naming.clean(db.get(BrandDB, working).key) + "-")
    assert copy["url"] != resolve.public_url(foreign_image.token), "its own file, its own address"
    assert anonymous.get("/media/" + copy["url"].rsplit("/media/", 1)[1]).content == gif(30, 40)


def _person(db, default_brand, other_brand=None):
    """A manager with a grant on the default brand, and on `other_brand` if given."""
    from app.auth import service as auth
    from app.auth.db_models import RoleDB

    user = auth.create_user(db, email=f"brands-{uuid.uuid4().hex[:8]}@example.invalid", role_key="manager",
                            brand_id=default_brand.id)
    if other_brand is not None:
        role = db.query(RoleDB).filter(RoleDB.key == "manager").one()
        auth.assign_role(db, user.id, role.id, brand_id=other_brand.id)
    return user


@pytest.fixture
def one_brand_person(db, default_brand):
    """A manager holding a grant on the default brand only."""
    yield from _session_of(db, _person(db, default_brand))


@pytest.fixture
def two_brand_person(db, default_brand, foreign_brand):
    """A manager holding grants on the default brand and the other one."""
    yield from _session_of(db, _person(db, default_brand, foreign_brand))


def _session_of(db, user):
    from sqlalchemy import text

    from app.auth import service as auth

    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, auth.csrf_token_for(token)
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM audit_events WHERE actor_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def test_without_a_grant_on_the_other_brand_its_images_are_not_there(db, foreign_image, foreign_brand,
                                                                     one_brand_person):
    client, csrf = one_brand_person
    assert client.get("/assets/", params={"brand": foreign_brand.id}).status_code == 404
    assert client.post(f"/assets/{foreign_image.id}/copy", headers={"X-CSRF-Token": csrf}).status_code == 404
