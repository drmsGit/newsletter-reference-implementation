"""A text names only the brand's entries, and never in a link (task-365; ADR-199).

Checked on save wherever a text is written: a module's own fields, the
envelope, content records and overrides. Only a changed value is judged.
"""
import pytest

from app.campaigns.db_models import ModuleInstanceDB
from app.campaigns.service import ModuleDataInvalid, create_module_for_variant, set_envelope_fields
from app.content.service import ContentTextInvalid, create_content, update_content_record
from app.expressions import service as dictionary
from app.expressions.checks import content_kinds, text_problems
from app.overrides.service import set_override_fields
from tests import test_render_skip as fixtures
from tests.test_api_guard import signed_in

db = fixtures.db
world = fixtures.world

KINDS = {"headline_medium": "text", "body_medium": "richtext", "button_url": "url", "image_url": "image",
         "image_alt": "text"}


@pytest.fixture
def brand(db, world):
    dictionary.by_name(db, world["brand"].id)    # the starters are in
    return world["brand"]


@pytest.mark.parametrize("field, value, says", [
    ("headline_medium", "{{nope}} hello", "not in this brand's dictionary"),
    ("headline_medium", "Hallo {{first_name}}", "recipient field"),
    ("button_url", "https://e.com/{{salutation_informal}}", "does not work in a link"),
    ("image_url", "https://cdn.e.com/{{salutation_informal}}.jpg", "does not work in a link"),
    ("image_alt", "{{salutation_informal}}", "alt text"),
    ("body_medium", "[read](https://e.com/{{salutation_informal}})", "link's address"),
])
def test_what_a_text_may_not_hold(db, brand, field, value, says):
    [(where, why)] = text_problems(db, brand.id, {field: value}, KINDS, alts=frozenset({"image_alt"}))
    assert where == field and says in why


@pytest.mark.parametrize("value", [
    "{{salutation_formal}} news", "{{ salutation_informal }} welcome", "[{{salutation_informal}}](https://e.com/x)",
    "no entries at all", "",
])
def test_what_a_text_may_hold(db, brand, value):
    assert text_problems(db, brand.id, {"body_medium": value}, KINDS) == []


def test_only_a_changed_value_is_judged(db, brand):
    old = {"headline_medium": "{{gone}} hello"}
    assert text_problems(db, brand.id, old, KINDS, previous=old) == []


def test_a_module_field_is_checked_on_save(db, world, brand):
    variant = world["variant"]()
    with pytest.raises(ModuleDataInvalid) as refused:
        create_module_for_variant(db, variant_id=variant.id, module_type="cta",
                                  module_data={"label": "{{nope}} go", "url": "https://e.com"}, brand_id=brand.id)
    assert refused.value.errors[0][0] == "label"
    db.rollback()
    assert create_module_for_variant(db, variant_id=variant.id, module_type="cta",
                                     module_data={"label": "{{salutation_informal}} go", "url": "https://e.com"},
                                     brand_id=brand.id) is not None


def test_the_subject_is_checked_on_save(db, world, brand):
    variant = world["variant"]()
    with pytest.raises(ValueError, match="subject"):
        set_envelope_fields(db, variant.id, {"subject": "{{first_name}}, hello"}, brand_id=brand.id)
    db.rollback()
    set_envelope_fields(db, variant.id, {"subject": "{{salutation_formal}} news"}, brand_id=brand.id)


def test_a_content_record_is_checked_on_save_and_answered_422(db, world, brand):
    record = create_content(db, title="t365-check", brand_id=brand.id, content={"headline_medium": "Plain"})
    world["made"]["records"].append(record.id)
    with pytest.raises(ContentTextInvalid):
        update_content_record(db, record.id, "t365-check", {"headline_medium": "{{nope}}"}, brand_id=brand.id)
    db.rollback()
    with signed_in(db) as (client, _token, csrf):
        response = client.patch(f"/content/{record.id}", json={"content": {"headline_medium": "{{nope}} hi"},
                                                               "groups": ["email"]},
                                headers={"X-CSRF-Token": csrf})
    assert response.status_code == 422 and "nope" in response.text
    assert content_kinds()[0]["button_url"] == "url"


def test_an_override_is_checked_on_save(db, world, brand):
    record = create_content(db, title="t365-override", brand_id=brand.id, content={"headline_medium": "Plain"})
    world["made"]["records"].append(record.id)
    variant = world["variant"]()
    module = create_module_for_variant(db, variant_id=variant.id, module_type="img_left",
                                       content_record_id=record.id, brand_id=brand.id)
    with pytest.raises(ValueError, match="nope"):
        set_override_fields(db, module.id, {"headline_medium": "{{nope}}"}, None, brand_id=brand.id, author="t")
    db.rollback()
    from app.overrides.db_models import ContentOverrideDB

    db.query(ContentOverrideDB).filter(ContentOverrideDB.module_instance_id == module.id).delete()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.id == module.id).delete()
    db.commit()


def test_the_editor_gets_a_refused_subject_on_its_field(db, world, brand):
    """Found in the live check (2026-10-16): the variant route answered this
    refusal with a 500. It is a 422 naming the field, like module data."""
    variant = world["variant"]()
    with signed_in(db) as (client, _token, csrf):
        current = client.get(f"/campaigns/{variant.campaign_id}/composition").json()
        version = next(v["variant"]["updated_at"] for v in current["variants"] if v["variant"]["id"] == variant.id)
        response = client.put(f"/campaigns/variants/{variant.id}", json={
            "name": variant.name, "envelope": {"subject": "Hi", "preheader": "{{nope}} a peek"}},
            headers={"X-CSRF-Token": csrf, "If-Match": version})
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "envelope", "preheader"]
