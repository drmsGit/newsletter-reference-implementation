"""The MJML email block set (task-371; ADR-198, ADR-131 addendum 2026-10-15).

Seven blocks: Hero, Headline, Image left, Image right, Column, Single text and
CTA, compiled from `storage/modules/email/*.mjml` by `npm run build:modules`
(CI checks the committed HTML is current). What is tested here is what the
backend adds: two Columns in a row share one 50:50 row, each side crediting its
own record; a lone one fills the left half; Single Stack is retired; only the
Hero and the CTA carry real buttons; the MJML head styles come with MJML blocks
and never with the hand-written modules alone.
"""
import re
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign, create_module_for_variant, update_module
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.content.service import create_content, create_content_version
from app.database import SessionLocal
from app.modules.registry import get_manifest, list_manifests
from app.rendering.frame import build_frame, render_frame
from app.rendering.service import email_document, render_variant_html
from app.rendering.tracking import content_id_from_url

TAG = f"blocks-{uuid.uuid4().hex[:6]}"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db):
    brand = ensure_default_brand(db)
    made = {"campaigns": [], "records": []}

    def record(name: str, **content) -> int:
        made_record = create_content(db, title=f"{TAG}-{name}", brand_id=brand.id, content={
            "headline_medium": f"{name} headline", "body_medium": f"{name} short", "body_long": f"{name} long",
            "button_label": f"Read {name}", "button_url": f"https://example.com/{name}",
            "image_url": f"https://cdn.example.com/{name}.jpg", "image_alt": f"{name} picture", **content})
        create_content_version(db, content_record_id=made_record.id, created_by="test", brand_id=brand.id)
        made["records"].append(made_record.id)
        return made_record.id

    def variant(*modules) -> int:
        """Modules as (type, record id or None, module_data or None)."""
        campaign = create_campaign(db, name=f"{TAG}-{uuid.uuid4().hex[:4]}", brand_id=brand.id, channel="email")
        made["campaigns"].append(campaign.id)
        v = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
        for module_type, record_id, data in modules:
            create_module_for_variant(db, variant_id=v.id, module_type=module_type, content_record_id=record_id,
                                      module_data=data, brand_id=brand.id)
        return v.id

    yield {"brand": brand, "record": record, "variant": variant}
    db.rollback()
    variants = [v for (v,) in db.query(VariantDB.id).filter(VariantDB.campaign_id.in_(made["campaigns"]))]
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variants)).delete(synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(variants)).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id.in_(made["campaigns"])).delete(synchronize_session=False)
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id.in_(made["records"])).delete(
        synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(made["records"])).delete(synchronize_session=False)
    db.commit()


def _sections(html: str) -> int:
    """MJML sections: each opens with a max-width:600px wrapper div."""
    return len(re.findall(r'<div\s+style="[^"]*max-width:600px', html))


def _buttons(html: str) -> list[str]:
    """The labels of real buttons: MJML's `mj-button` is a styled link."""
    return re.findall(r'<a [^>]*style="display:inline-block[^>]*>\s*([^<]+?)\s*<', html)


def _credited(html: str, label: str) -> int | None:
    """The content id the link reading `label` credits."""
    match = re.search(r'<a [^>]*href="([^"]+)"[^>]*>\s*' + re.escape(label), html)
    assert match, f"no link reading {label!r}"
    return content_id_from_url(match.group(1).replace("&amp;", "&"))


class TestTwoColumns:
    def test_two_columns_in_a_row_share_one_row_each_crediting_its_own_record(self, db, world):
        a, b = world["record"]("Alpha"), world["record"]("Beta")
        html = render_variant_html(db, world["variant"](("column", a, None), ("column", b, None)))
        assert _sections(html) == 1, "one 50:50 row, not two"
        assert html.index("Alpha headline") < html.index("Beta headline"), "the first module is the left side"
        assert _credited(html, "Read Alpha") == a and _credited(html, "Read Beta") == b
        assert f'data-content-id="{a}"' in html and f'data-content-id="{b}"' in html

    def test_a_lone_column_fills_the_left_half(self, db, world):
        a = world["record"]("Alpha")
        html = render_variant_html(db, world["variant"](("column", a, None), ("cta", None,
                                                         {"label": "Go", "url": "https://example.com/go"})))
        assert _sections(html) == 2
        assert html.count('class="mj-column-per-50') == 2, "its half and an empty one"
        assert _credited(html, "Read Alpha") == a

    def test_three_in_a_row_are_a_pair_and_a_lone_one(self, db, world):
        a, b, c = (world["record"](n) for n in ("Alpha", "Beta", "Gamma"))
        html = render_variant_html(db, world["variant"](*(("column", r, None) for r in (a, b, c))))
        assert _sections(html) == 2
        assert _credited(html, "Read Gamma") == c

    def test_an_unbound_column_between_two_does_not_break_the_row(self, db, world):
        """A module that shows nothing leaves a comment, not a gap (ADR-086)."""
        a, b = world["record"]("Alpha"), world["record"]("Beta")
        html = render_variant_html(db, world["variant"](("column", a, None), ("column", None, None),
                                                         ("column", b, None)))
        assert _sections(html) == 1
        assert _credited(html, "Read Alpha") == a and _credited(html, "Read Beta") == b

    def test_a_hidden_field_stays_hidden_on_its_side_only(self, db, world):
        a, b = world["record"]("Alpha"), world["record"]("Beta")
        variant_id = world["variant"](("column", a, None), ("column", b, None))
        left = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant_id,
                                                ModuleInstanceDB.module_type == "column").order_by(
            ModuleInstanceDB.position).first()
        left.hidden_fields = ["image_url"]
        db.commit()
        html = render_variant_html(db, variant_id)
        assert "Alpha.jpg" not in html and "Beta.jpg" in html

    def test_the_frame_pairs_them_as_the_preview_does(self, db, world):
        a, b = world["record"]("Alpha"), world["record"]("Beta")
        variant_id = world["variant"](("column", a, None), ("column", b, None))
        sent = render_frame(db, build_frame(db, variant_id))[0].body
        assert _sections(sent) == 1
        assert _credited(sent, "Read Alpha") == a and _credited(sent, "Read Beta") == b


class TestTheBlocks:
    def test_only_the_hero_and_the_cta_carry_buttons(self, db, world):
        a = world["record"]("Alpha", headline_hero="Big news", button_label_hero="Shop now")
        html = render_variant_html(db, world["variant"](
            ("hero", a, None), ("img_left", a, None), ("img_right", a, None), ("single_text", a, None),
            ("cta", None, {"label": "Go", "url": "https://example.com/go"})))
        assert sorted(_buttons(html)) == ["Go", "Shop now"]
        assert html.count("Read Alpha&nbsp;→") == 3, "the others are text links"

    def test_image_right_comes_first_in_the_source_so_it_stacks_first(self, db, world):
        a = world["record"]("Alpha")
        html = render_variant_html(db, world["variant"](("img_right", a, None)))
        assert "direction:rtl" in html
        assert html.index("Alpha.jpg") < html.index("Alpha headline")

    def test_single_text_uses_the_long_body(self, db, world):
        a = world["record"]("Alpha")
        html = render_variant_html(db, world["variant"](("single_text", a, None)))
        assert "Alpha long" in html and "Alpha short" not in html

    @pytest.mark.parametrize("second, buttons", [({}, 1), ({"label_2": "More"}, 1),
                                                 ({"label_2": "More", "url_2": "https://example.com/more"}, 2)])
    def test_the_cta_shows_a_second_button_only_when_both_are_given(self, db, world, second, buttons):
        html = render_variant_html(db, world["variant"](
            ("cta", None, {"label": "Go", "url": "https://example.com/go", **second})))
        assert len(_buttons(html)) == buttons

    def test_the_headline_block_is_an_h2_and_not_content(self, db, world):
        html = render_variant_html(db, world["variant"](("headline", None, {"heading": "This week"})))
        assert re.search(r"<h2[^>]*>This week</h2>", html)
        assert get_manifest("email", "headline").decorative


class TestRetired:
    def test_single_stack_is_not_offered(self):
        offered = {m.name for m in list_manifests("email", offered=True)}
        assert "single_stack" not in offered
        assert {"hero", "headline", "img_left", "img_right", "column", "single_text", "cta"} <= offered
        assert "single_stack" in {m.name for m in list_manifests("email")}, "still known, so it renders"

    def test_adding_it_is_refused(self, db, world):
        with pytest.raises(ValueError, match="retired"):
            world["variant"](("single_stack", None, {}))

    def test_one_already_there_renders_and_can_be_edited(self, db, world):
        a = world["record"]("Alpha")
        variant_id = world["variant"](("img_left", a, None), ("img_left", a, None))
        module = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant_id,
                                                  ModuleInstanceDB.module_type == "img_left").order_by(
            ModuleInstanceDB.position).first()
        module.module_type = "single_stack"  # as one made before it was retired
        db.commit()
        assert "Alpha headline" in render_variant_html(db, variant_id)
        updated = update_module(db, module.id, module_type="single_stack", content_record_id=a,
                                            module_data={"section_heading": "Still here"},
                                            brand_id=world["brand"].id)
        assert updated is not None
        with pytest.raises(ValueError, match="retired"):
            other = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant_id,
                                                     ModuleInstanceDB.module_type == "img_left").one()
            update_module(db, other.id, module_type="single_stack", brand_id=world["brand"].id)


class TestTheHead:
    def test_the_responsive_rules_come_with_an_mjml_block(self, db, world):
        a = world["record"]("Alpha")
        html = render_variant_html(db, world["variant"](("img_left", a, None)))
        assert "@media only screen and (min-width:480px)" in html
        assert 'name="viewport"' in html, "without it a phone lays the email out wide and nothing stacks"

    def test_a_document_of_hand_written_modules_is_unchanged(self):
        html = email_document(['<div data-module-id="1"><p class="module-body">Hi</p></div>'])
        assert "@media" not in html and "mj-column" not in html and "viewport" not in html
