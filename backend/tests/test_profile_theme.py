"""A brand profile's look and link tags reach the email (task-354; ADR-194,
addendum 2026-10-11 (third)).

brand.css names profile values as `var(--field, fallback)`; the renderer fills
them in before inlining, because mail programs cannot read CSS variables. The
values also reach every module template as `profile`, for templates whose
styles are attributes (MJML, ADR-131). Every link a module renders carries the
profile's UTM tags, never the legal footer's; utm_campaign and utm_content are
the campaign's and variant's names as slugs, frozen at snapshot time.
"""
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.brand_profiles import service as profiles
from app.brand_profiles.db_models import BrandProfileDB
from app.brand_profiles.theme import link_params, resolve_css, slug
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign, create_module_for_variant, set_envelope_fields
from app.database import SessionLocal
from app.rendering.frame import build_frame, render_frame
from app.rendering.tracking import tag_params

LEGAL = {
    "legal_company_name": "Theme GmbH",
    "legal_address": "Example Street 1",
    "imprint_url": "https://example.test/imprint",
    "privacy_url": "https://example.test/privacy",
    "unsubscribe_text": "Unsubscribe",
}


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# --- brand.css ---------------------------------------------------------------

CSS = """
.a { color: var(--colour_button, #1a1a1a); }
.b { font-family: var(--font_family, Arial, Helvetica, sans-serif); }
.c { padding: var(--size_body, 16px) 0; }
.d { content: var(--legal_company_name, none); }
"""


def test_a_value_replaces_its_variable_and_an_empty_one_falls_back():
    out = resolve_css(CSS, {"colour_button": "#ff0000", "size_body": ""})
    assert "color: #ff0000;" in out
    assert "padding: 16px 0;" in out, "an empty value falls back"
    assert "font-family: Arial, Helvetica, sans-serif;" in out, "a fallback may hold commas"
    assert "var(" not in out, "no email may contain a CSS variable"


def test_only_style_values_are_filled_in():
    """A text field named in brand.css falls back: free text never reaches CSS."""
    out = resolve_css(CSS, {"legal_company_name": "x; } body { display:none"})
    assert "content: none;" in out


# --- link tags ---------------------------------------------------------------

def test_slugs_are_readable_labels():
    assert slug("Spring Sale 2026!") == "spring-sale-2026"
    assert slug("  Variant  B ") == "variant-b"
    assert slug("Ümlaut & Co") == "mlaut-co"


def test_no_tags_without_a_source():
    assert link_params({"utm_medium": "email"}, "Spring", "A") == []


def test_tags_come_from_the_profile_and_the_names():
    params = link_params(
        {"utm_source": "newsletter", "utm_medium": "email", "utm_extra": "ref=nl\n\nchannel=mail"},
        "Spring Sale", "Variant B",
    )
    assert params == [["utm_source", "newsletter"], ["utm_medium", "email"],
                      ["utm_campaign", "spring-sale"], ["utm_content", "variant-b"],
                      ["ref", "nl"], ["channel", "mail"]]


def test_extras_never_carry_attribution_nor_repeat_a_tag():
    """Codex doc-15: stored before the save-time refusal existed, still dropped."""
    params = link_params({"utm_source": "nl", "utm_extra": "nl_content=42\nutm_source=other\nref=x"},
                         "Spring", "A")
    assert params == [["utm_source", "nl"], ["utm_campaign", "spring"], ["utm_content", "a"], ["ref", "x"]]
    assert "nl_content" not in tag_params('<a href="https://a.test/">x</a>', [["nl_content", "42"]])


def test_a_links_own_keys_are_kept_and_other_links_are_left_alone():
    html = ('<a href="https://shop.test/x?utm_source=partner&a=1">x</a>'
            '<a href="mailto:hi@example.test">m</a><a href="#top">t</a>')
    out = tag_params(html, [["utm_source", "newsletter"], ["utm_medium", "email"]])
    assert 'href="https://shop.test/x?utm_source=partner&amp;a=1&amp;utm_medium=email"' in out \
        or 'href="https://shop.test/x?utm_source=partner&a=1&utm_medium=email"' in out
    assert 'href="mailto:hi@example.test"' in out and 'href="#top"' in out


def test_an_escaped_ampersand_in_a_link_stays_a_separator():
    """A template writes & in an href as &amp;; it must not become a key."""
    out = tag_params('<a href="https://shop.test/x?a=1&amp;b=2">x</a>', [["utm_source", "nl"]])
    assert "amp%3Bb" not in out and "amp;b" not in out
    assert "a=1&b=2&utm_source=nl" in out


# --- validation ----------------------------------------------------------------

@pytest.mark.parametrize("values, field", [
    ({"font_family": "Arial; } body { display:none"}, "font_family"),
    ({"utm_extra": "no equals sign"}, "utm_extra"),
    ({"utm_extra": "ref=nl\nnl_content=42"}, "utm_extra"),   # click attribution is the platform's
])
def test_values_that_would_break_css_or_links_are_refused(values, field):
    with pytest.raises(profiles.ProfileInvalid) as refused:
        profiles.clean_values(values)
    assert [loc[-1] for loc, _ in refused.value.errors] == [field]


def test_good_look_and_tag_values_are_kept():
    values = {"font_family": "'Open Sans', Arial, sans-serif", "utm_extra": "ref=nl\nx.y-z=1"}
    assert profiles.clean_values(values) == values


# --- in the email ----------------------------------------------------------------

@pytest.fixture
def world(db):
    """An email variant with one typed-in button, on a profile with UTM tags."""
    brand = ensure_default_brand(db)
    profile = BrandProfileDB(brand_id=brand.id, name=f"Theme {uuid.uuid4().hex[:6]}",
                             field_values={**LEGAL, "utm_source": "newsletter", "utm_medium": "email"})
    db.add(profile)
    db.commit()
    campaign = create_campaign(db, name="Spring Sale 2026", brand_id=brand.id, channel="email")
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    variant.brand_profile_id = profile.id
    variant.name = "Variant B"
    db.commit()
    set_envelope_fields(db, variant.id, {"subject": "Hello"}, brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="cta",
                              module_data={"label": "Shop", "url": "https://shop.test/sale"},
                              brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="editorial",
                              module_data={"text": "Spring is here."}, brand_id=brand.id)
    made = [profile.id]
    yield {"brand": brand, "variant": variant, "profile": profile, "campaign": campaign, "made": made}
    db.rollback()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(BrandProfileDB).filter(BrandProfileDB.id.in_(made)).delete(synchronize_session=False)
    db.commit()


def _button_style(body: str) -> str:
    """The CTA's button: since task-371 an MJML button, styled by attributes
    from the profile rather than by a brand.css class (ADR-198)."""
    start = body.index('href="https://shop.test/sale')
    tag_start = body.rindex("<a", 0, start)
    return body[tag_start:body.index(">", start)]


def _editorial_text_style(body: str) -> str:
    """The style of the editorial's text: the div an MJML text block wraps it
    in, inside the cell marked module-editorial (task: editorial as MJML,
    2026-10-17). It carries the shared text attributes the profile sets."""
    start = body.index('class="module-editorial"')
    div = body.index("<div", start)
    return body[div:body.index(">", div)]


def test_two_profiles_give_two_looks_from_one_variant(db, world):
    """AC1: the same variant, two profiles: button colour, text colour and
    text size differ. (The font family applies inside the content modules'
    wrapper, as today; resolve_css's own test covers it.)"""
    plain = render_frame(db, build_frame(db, world["variant"].id))[0].body
    world["profile"].field_values = {**world["profile"].field_values, "colour_button": "#ff0000",
                                     "colour_body_text": "#00aa00", "size_body": "18px"}
    db.commit()
    themed = render_frame(db, build_frame(db, world["variant"].id))[0].body
    assert "#1a1a1a" in _button_style(plain), "an empty field keeps today's look"
    assert "#ff0000" in _button_style(themed)
    assert "16px" in _editorial_text_style(plain) and "#444444" in _editorial_text_style(plain)
    assert "18px" in _editorial_text_style(themed) and "#00aa00" in _editorial_text_style(themed)
    assert "var(" not in plain and "var(" not in themed


def test_a_profile_value_reaches_a_module_template(db, world, monkeypatch):
    """AC2: for templates whose styles are attributes (MJML), not CSS."""
    import app.rendering.service as rendering

    real = rendering.get_template_html

    def template(channel, module_type):
        if module_type == "cta":
            return '<div data-module-type="cta" data-colour="{{ profile.colour_button }}">{{ label }}</div>'
        return real(channel, module_type)

    monkeypatch.setattr(rendering, "get_template_html", template)
    world["profile"].field_values = {**world["profile"].field_values, "colour_button": "#00ff00"}
    db.commit()
    body = render_frame(db, build_frame(db, world["variant"].id))[0].body
    assert 'data-colour="#00ff00"' in body


def test_module_links_carry_the_tags_and_legal_links_do_not(db, world):
    """AC3, on the frame path a send takes."""
    body = render_frame(db, build_frame(db, world["variant"].id),
                        unsubscribe={"url": "https://app.test/unsubscribe/tok", "brand": "x"})[0].body
    assert ("https://shop.test/sale?utm_source=newsletter&amp;utm_medium=email"
            "&amp;utm_campaign=spring-sale-2026&amp;utm_content=variant-b") in body
    assert 'href="https://example.test/imprint"' in body
    assert 'href="https://example.test/privacy"' in body
    assert 'href="https://app.test/unsubscribe/tok"' in body


def test_the_tags_are_frozen_with_the_snapshot(db, world):
    frame = build_frame(db, world["variant"].id)
    world["campaign"].name = "Renamed later"
    world["profile"].field_values = {**world["profile"].field_values, "utm_source": "changed"}
    db.commit()
    body = render_frame(db, frame)[0].body
    assert "utm_campaign=spring-sale-2026" in body and "utm_source=newsletter" in body
    assert "renamed-later" not in body and "changed" not in body


def test_the_live_render_carries_the_same_look_and_tags(db, world):
    """Preview and test send render live; they match what a snapshot would send."""
    from app.rendering.service import legal_footer_html, render_variant_html

    frame = build_frame(db, world["variant"].id)
    live = render_variant_html(db, world["variant"].id, mode="send",
                               footer=legal_footer_html(frame["brand_profile"]))
    assert live == render_frame(db, frame)[0].body


def test_a_frame_without_tags_or_look_renders_untagged(db, world):
    """Frames made before this slice carry no link parameters: as sent."""
    frame = build_frame(db, world["variant"].id)
    frame.pop("link_params")
    frame["brand_profile"]["values"] = dict(LEGAL)
    body = render_frame(db, frame)[0].body
    assert 'href="https://shop.test/sale"' in body
    assert "#1a1a1a" in _button_style(body)
