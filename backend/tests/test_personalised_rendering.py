"""Entries reach the texts, per recipient, and a sent email rebuilds exactly
(task-365; ADR-199).

The subject, the preheader and module and content text take a brand's
entries ({{salutation_formal}}); links never do. Substitution happens after
escaping and never through Jinja. A frame (version 4) freezes the entries in
the message's language; the delivery record keeps the values used, and a
rebuild uses those, never the recipient as they are now.
"""
import pytest

from app.campaigns.db_models import ModuleInstanceDB
from app.campaigns.service import set_envelope_fields
from app.campaigns.db_models import VariantDB
from app.content.db_models import ContentVersionDB
from app.delivery.db_models import DeliveryExecutionDB
from app.delivery.exclusion import REASON_PERSONAL_MISSING, STAGE_RENDER
from app.delivery.service import reconstruct_delivery, test_variant as run_test
from app.expressions import service as dictionary
from app.expressions.rules import resolve
from app.expressions.substitute import message_language
from app.rendering.frame import build_frame, expression_refusal, render_frame
from app.rendering.service import render_variant
from app.recipients.db_models import RecipientDB
from tests import test_render_skip as fixtures

db = fixtures.db
world = fixtures.world

FORMAL, INFORMAL = "{{salutation_formal}}", "{{ salutation_informal }}"


@pytest.fixture
def setup(db, world):
    """An email variant whose subject, typed-in CTA and catalogue pick use
    the brand's starter entries, and the texts each should read."""
    brand = world["brand"]
    entries = dictionary.by_name(db, brand.id)        # starts the dictionary if needed
    variant = world["variant"](static=True)
    _, language = message_language(db, variant)
    set_envelope_fields(db, variant.id, {"subject": f"{FORMAL} news", "preheader": f"{INFORMAL} a peek"},
                        brand_id=brand.id)
    cta = db.query(ModuleInstanceDB).filter_by(variant_id=variant.id, module_type="cta").one()
    cta.module_data = {"label": f"{INFORMAL} go", "url": "https://example.com/go"}
    db.commit()

    def says(name, person):
        fields = None if person is None else {"gender": person.gender, "first_name": person.first_name,
                                               "last_name": person.last_name}
        return resolve(entries[name].languages[language], fields)

    def person(gender=None, first=None, last=None, **kw):
        p = world["person"](**kw)
        p.gender, p.first_name, p.last_name = gender, first, last
        db.commit()
        return p

    return {"variant": variant, "says": says, "person": person, "language": language, "brand": brand}


def test_the_preview_shows_fallbacks_without_a_recipient(db, setup):
    artifact = render_variant(db, setup["variant"].id)
    says = setup["says"]
    assert artifact.envelope["subject"] == f"{says('salutation_formal', None)} news"
    assert f"{says('salutation_informal', None)} go" in artifact.body
    assert "{{" not in artifact.body


def test_the_preview_shows_a_picked_recipients_text(db, setup):
    anna = setup["person"]("female", "Anna", "Müller")
    artifact = render_variant(db, setup["variant"].id, recipient_id=anna.id)
    assert artifact.envelope["subject"] == f"{setup['says']('salutation_formal', anna)} news"
    assert "Müller" in artifact.envelope["subject"]
    assert f"{setup['says']('salutation_informal', anna)} go" in artifact.body


def test_a_recipients_value_is_escaped_never_markup(db, setup):
    eve = setup["person"]("female", "<b>Eve</b>", "Smith")
    body = render_variant(db, setup["variant"].id, recipient_id=eve.id).body
    assert "<b>Eve</b>" not in body and "&lt;b&gt;Eve&lt;/b&gt;" in body


def test_rich_text_takes_an_entry_but_a_link_target_never_does(db, setup):
    """Substituted outside tags only: the label of a link, never its href."""
    from app.expressions.substitute import Personal
    from app.rendering.service import render_rich_text

    personal = Personal({"salutation_informal": "Hi <Ann>"})
    html = str(personal.markup(render_rich_text(
        "[{{salutation_informal}}](https://example.com/{{salutation_informal}}) and **{{salutation_informal}}**")))
    assert 'href="https://example.com/{{salutation_informal}}"' in html
    assert ">Hi &lt;Ann&gt;</a>" in html and "<strong>Hi &lt;Ann&gt;</strong>" in html


def test_a_frame_freezes_the_language_and_the_entries(db, setup):
    frame = build_frame(db, setup["variant"].id)
    assert frame["frame_version"] == 4
    assert frame["expressions"]["language"] == setup["language"]
    assert {"salutation_formal", "salutation_informal"} <= set(frame["expressions"]["entries"])


def test_a_send_records_the_values_and_rebuilds_them_after_everything_changed(db, world, setup):
    anna = setup["person"]("female", "Anna", "Müller", picks=True)
    send, rows = world["send"](setup["variant"], [anna])
    assert rows[anna.id][0] == "sent", rows
    execution = db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id).one()
    formal = setup["says"]("salutation_formal", anna)
    assert execution.delivery_record["personal"]["salutation_formal"] == formal
    before = reconstruct_delivery(db, execution.id, brand_id=setup["brand"].id)
    assert before["hash_matches"] is True and before["envelope"]["subject"] == f"{formal} news"

    # Today she is someone else, and the entry reads differently.
    row = db.get(RecipientDB, anna.id)
    row.first_name, row.last_name, row.gender = "Hanna", "Meier", "diverse"
    entry = dictionary.by_name(db, setup["brand"].id)["salutation_formal"]
    original = entry.languages
    entry.languages = {code: {**spec, "fallback": "Changed,"} for code, spec in original.items()}
    db.commit()
    try:
        after = reconstruct_delivery(db, execution.id, brand_id=setup["brand"].id)
    finally:
        entry.languages = original
        db.commit()
    assert after["hash_matches"] is True
    assert after["body"] == before["body"] and after["envelope"] == before["envelope"]


def test_a_text_using_an_entry_without_the_language_is_refused_before_it_goes_out(db, world, setup):
    cta = db.query(ModuleInstanceDB).filter_by(variant_id=setup["variant"].id, module_type="cta").one()
    cta.module_data = {"label": "{{no_such_entry}} go", "url": "https://example.com/go"}
    db.commit()
    assert "{{no_such_entry}}" in expression_refusal(build_frame(db, setup["variant"].id))
    with pytest.raises(ValueError, match="no_such_entry"):
        run_test(db, setup["variant"].id, to="t365@example.invalid", provider="mock", from_address=None,
                 recipient_id=None, brand_id=setup["brand"].id)
    anna = setup["person"]("female", "Anna", "Müller", picks=True)
    with pytest.raises(ValueError, match="no_such_entry"):
        world["send"](setup["variant"], [anna])


def test_a_pick_using_an_entry_without_the_language_excludes_that_recipient(db, world, setup):
    record_id = world["made"]["records"][0]
    version = db.query(ContentVersionDB).filter_by(content_record_id=record_id).order_by(
        ContentVersionDB.version_number.desc()).first()
    original = version.content
    version.content = {**original, "headline_medium": "{{no_such_entry}} picked for you"}
    db.commit()
    try:
        anna = setup["person"]("female", "Anna", "Müller", picks=True)
        _, rows = world["send"](setup["variant"], [anna])
    finally:
        version.content = original
        db.commit()
    assert rows[anna.id] == ("excluded", f"{STAGE_RENDER}: {REASON_PERSONAL_MISSING}: {{{{no_such_entry}}}}")


def test_a_push_takes_entries_in_its_title_and_body(db, world, setup):
    push = world["variant"]("push", static=False)
    module = db.query(ModuleInstanceDB).filter_by(variant_id=push.id).one()
    frame = build_frame(db, push.id)
    frame["modules"] = [{**e, "kind": "static", "variables": {"push_title": f"{INFORMAL} news",
                                                               "push_body": "Body", "push_link": "https://e.com"}}
                        if e["module_id"] == module.id else e for e in frame["modules"]]
    jan = setup["person"]("male", "Jan", "Jansen", channel="push")
    artifact, _ = render_frame(db, frame, recipient_id=jan.id)
    _, language = message_language(db, db.get(VariantDB, push.id))
    assert artifact.fields["push_title"] == f"{setup['says']('salutation_informal', jan)} news"


def test_a_frame_from_before_version_4_renders_as_it_was(db, setup):
    frame = build_frame(db, setup["variant"].id)
    frame["frame_version"] = 3
    frame.pop("expressions")
    artifact, _ = render_frame(db, frame)
    assert artifact.envelope["subject"] == f"{FORMAL} news", "no substitution, as sent before"
    assert artifact.personal is None


def test_an_images_alt_text_and_link_fields_take_no_entry():
    from app.expressions.substitute import Personal
    from app.modules.registry import get_manifest

    personal = Personal({"salutation_informal": "Hi Ann,"})
    fields = personal.fields({"image_alt": "{{salutation_informal}}", "button_url": "https://e.com/{{salutation_informal}}",
                              "headline_medium": "{{salutation_informal}} hello"}, get_manifest("email", "img_left"))
    assert fields["image_alt"] == "{{salutation_informal}}"
    assert fields["button_url"] == "https://e.com/{{salutation_informal}}"
    assert fields["headline_medium"] == "Hi Ann, hello"


def test_the_version_decides_not_the_key(db, setup):
    """A reader keys on frame_version (frame.py): below 4, no substitution,
    whatever the frame holds."""
    frame = {**build_frame(db, setup["variant"].id), "frame_version": 3}
    artifact, _ = render_frame(db, frame)
    assert artifact.envelope["subject"] == f"{FORMAL} news"
