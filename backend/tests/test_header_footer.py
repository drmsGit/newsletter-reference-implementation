"""The visible header and footer are modules that render from the email's brand
profile (task-351; ADR-194 and its 2026-10-11 addenda, the fourth for this).

A manager places them or leaves them out. The header shows the profile's logo
and menu; the footer one note for this email, then the profile's footer links,
hotline and text, before the fixed legal footer. Both are decorative: an email
of only decorative modules and the envelope is nothing to show (ADR-086).
Link lists are one link per line, "Label | https://address"; every address is
https.
"""
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.brand_profiles import service as profiles
from app.brand_profiles.db_models import BrandProfileDB
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign, create_module_for_variant, set_envelope_fields
from app.database import SessionLocal
from app.modules.registry import get_manifest, list_manifests
from app.rendering.frame import build_frame, render_frame, what_rendered
from app.rendering.service import parse_links

HEADER_FOOTER = {
    "legal_company_name": "Header GmbH",
    "legal_address": "Example Street 1",
    "imprint_url": "https://example.test/imprint",
    "privacy_url": "https://example.test/privacy",
    "unsubscribe_text": "Unsubscribe",
    "logo": "https://cdn.example.test/logo.png",
    "logo_alt": "Example Shop",
    "logo_link": "https://example.test/",
    "menu_links": "Shop | https://example.test/shop\nService | https://example.test/help",
    "footer_links": "Stores | https://example.test/stores",
    "service_hotline": "Call 0800 123 456",
    "footer_text": "Prices include VAT.",
    "utm_source": "newsletter",
}


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# --- link lists and https -------------------------------------------------------

def test_a_link_list_is_one_link_per_line_in_order():
    assert parse_links("Shop | https://a.test/shop\n\n  Help|https://a.test/help  ") == [
        {"label": "Shop", "url": "https://a.test/shop"},
        {"label": "Help", "url": "https://a.test/help"},
    ]
    assert parse_links(None) == [] and parse_links("") == []


@pytest.mark.parametrize("field, value", [
    ("menu_links", "Shop https://example.test/shop"),        # no separator
    ("menu_links", " | https://example.test/shop"),          # no label
    ("menu_links", "Shop | http://example.test/shop"),       # not https
    ("logo", "http://cdn.example.test/logo.png"),            # images are https
    ("imprint_url", "http://example.test/imprint"),          # and so are links
])
def test_addresses_must_be_https_and_lines_well_formed(field, value):
    with pytest.raises(profiles.ProfileInvalid) as refused:
        profiles.clean_values({field: value})
    assert [loc[-1] for loc, _ in refused.value.errors] == [field]


def test_well_formed_lists_and_https_addresses_are_kept():
    values = {k: HEADER_FOOTER[k] for k in ("logo", "logo_link", "menu_links", "footer_links")}
    assert profiles.clean_values(values) == values


# --- the manifests ------------------------------------------------------------------

def test_header_and_footer_are_decorative_and_nothing_else_is():
    decorative = {m.name for m in list_manifests("email") if m.decorative}
    # And the Headline block (ADR-198): a heading alone is nothing to show.
    assert decorative == {"header", "footer", "headline"}
    assert [v.name for v in get_manifest("email", "header").variables] == []
    assert [v.name for v in get_manifest("email", "footer").variables] == ["footer_note"]
    assert not get_manifest("email", "footer").variables[0].required


# --- in the email -------------------------------------------------------------------

@pytest.fixture
def world(db):
    brand = ensure_default_brand(db)
    profile = BrandProfileDB(brand_id=brand.id, name=f"HF {uuid.uuid4().hex[:6]}",
                             field_values=dict(HEADER_FOOTER))
    db.add(profile)
    db.commit()
    campaign = create_campaign(db, name="Header Check", brand_id=brand.id, channel="email")
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    variant.brand_profile_id = profile.id
    db.commit()
    set_envelope_fields(db, variant.id, {"subject": "Hello"}, brand_id=brand.id)
    yield {"brand": brand, "variant": variant, "profile": profile, "campaign": campaign}
    db.rollback()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(BrandProfileDB).filter(BrandProfileDB.id == profile.id).delete()
    db.commit()


def _place(db, world, module_type, data=None):
    create_module_for_variant(db, variant_id=world["variant"].id, module_type=module_type,
                              module_data=data, brand_id=world["brand"].id)


def _body(db, world, **kwargs):
    return render_frame(db, build_frame(db, world["variant"].id), **kwargs)[0].body


def test_the_header_shows_the_profiles_logo_and_menu(db, world):
    _place(db, world, "header")
    body = _body(db, world)
    assert 'src="https://cdn.example.test/logo.png"' in body and 'alt="Example Shop"' in body
    assert ">Shop</a>" in body and ">Service</a>" in body
    assert body.index(">Shop</a>") < body.index(">Service</a>"), "in the order written"
    # Tagged like every module link, never as content (ADR-182 point 3).
    assert "https://example.test/shop?utm_source=newsletter" in body
    assert "nl_content" not in body


def test_switching_the_profile_switches_the_header(db, world):
    _place(db, world, "header")
    other = BrandProfileDB(brand_id=world["brand"].id, name=f"HF other {uuid.uuid4().hex[:6]}",
                           field_values={**HEADER_FOOTER, "logo": "https://cdn.example.test/dark.png",
                                         "menu_links": "Sale | https://example.test/sale"})
    db.add(other)
    db.commit()
    try:
        world["variant"].brand_profile_id = other.id
        db.commit()
        body = _body(db, world)
        assert "dark.png" in body and ">Sale</a>" in body and ">Shop</a>" not in body
    finally:
        world["variant"].brand_profile_id = world["profile"].id
        db.commit()
        db.query(BrandProfileDB).filter(BrandProfileDB.id == other.id).delete()
        db.commit()


def test_an_empty_profile_leaves_the_header_out(db, world):
    world["profile"].field_values = {k: v for k, v in HEADER_FOOTER.items()
                                     if k not in ("logo", "logo_alt", "logo_link", "menu_links")}
    db.commit()
    _place(db, world, "header")
    body = _body(db, world)
    assert "<img" not in body and ">Shop</a>" not in body
    assert 'class="module-header"' not in body, "not even an empty frame of it"


def test_the_footer_shows_its_note_then_the_profile_then_the_legal_footer(db, world):
    _place(db, world, "footer", {"footer_note": "Only this week: free shipping."})
    body = _body(db, world, unsubscribe={"url": "https://app.test/unsubscribe/tok", "brand": "x"})
    order = ["Only this week: free shipping.", ">Stores</a>", "Call 0800 123 456",
             "Prices include VAT.", ">Imprint</a>"]
    positions = [body.index(text) for text in order]
    assert positions == sorted(positions), "note, links, hotline, text, then the legal footer"


def test_a_footer_without_a_note_still_shows_the_profile_part(db, world):
    _place(db, world, "footer")
    body = _body(db, world)
    assert ">Stores</a>" in body and "Prices include VAT." in body


def test_decorative_modules_alone_are_nothing_to_show(db, world):
    _place(db, world, "header")
    _place(db, world, "footer", {"footer_note": "A note"})
    frame = build_frame(db, world["variant"].id)
    assert what_rendered(frame, []) == (False, 0)
    _place(db, world, "cta", {"label": "Shop", "url": "https://example.test/shop"})
    assert what_rendered(build_frame(db, world["variant"].id), []) == (True, 0)
