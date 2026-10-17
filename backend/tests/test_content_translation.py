"""A record's language, and translations as linked records (task-369;
ADR-200, ADR-140 addendum 2026-10-17).

What these pin: a language is one of the brand's profile languages or not
set, and is locked while a record is linked; a slot picks only records in its
variant's language or with none; a translation is a new record in the same
brand with the translated text, the links, images and categories copied, and
nothing a person must decide (published, ready, machine ready); refusals cost
nothing; a placeholder or link the model changed keeps the original's text;
and a changed original shows per field and is taken back with ticks.
"""
import json
import uuid

import pytest
from sqlalchemy import text

from app.ai import service as ai_service
from app.ai.adapters.mock import MockAIProvider
from app.ai.db_models import AIPromptDB, AIRunDB
from app.ai.tasks import content_translate
from app.audit.db_models import AuditEventDB
from app.auth.service import ensure_default_brand
from app.brand_profiles.db_models import BrandProfileDB
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentChannelReadinessDB, ContentRecordDB,
)
from app.content.service import assign_category_to_content, create_category, create_content
from tests.test_api_guard import signed_in

TAG = f"t369-{uuid.uuid4().hex[:5]}"
ORIGINAL = {
    "headline_medium": "Three days in Lisbon",
    "body_medium": "Hello {{salutation_informal}}, ride **tram 28** past [the tiles](https://example.invalid/tiles).",
    "button_label": "Read more",
    "button_url": "https://example.invalid/lisbon",
    "image_url": "https://example.invalid/tram.png",
    "image_alt": "A yellow tram",
}


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    yield session
    session.rollback()
    records = [r for (r,) in session.query(ContentRecordDB.id).filter(ContentRecordDB.title.like(f"%{TAG}%"))]
    session.query(AuditEventDB).filter(AuditEventDB.subject_type == "content",
                                       AuditEventDB.subject_id.in_(records)).delete(synchronize_session=False)
    session.query(AIRunDB).filter(AIRunDB.task_key == content_translate.TASK_KEY).delete(synchronize_session=False)
    session.query(AIPromptDB).filter(AIPromptDB.task_key == content_translate.TASK_KEY).delete(synchronize_session=False)
    session.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.content_id.in_(records)).delete(synchronize_session=False)
    session.query(ContentChannelReadinessDB).filter(
        ContentChannelReadinessDB.content_id.in_(records)).delete(synchronize_session=False)
    for rid in records:
        session.execute(text("DELETE FROM content_versions WHERE content_record_id = :r"), {"r": rid})
    session.query(ContentRecordDB).filter(ContentRecordDB.id.in_(records)).update(
        {"translation_of_id": None}, synchronize_session=False)
    session.query(ContentRecordDB).filter(ContentRecordDB.id.in_(records)).delete(synchronize_session=False)
    session.query(CategoryDB).filter(CategoryDB.name.like(f"{TAG}%")).delete(synchronize_session=False)
    session.query(BrandProfileDB).filter(BrandProfileDB.name.like(f"{TAG}%")).delete(synchronize_session=False)
    session.commit()
    session.close()


@pytest.fixture
def world(db):
    brand = ensure_default_brand(db)
    db.add(BrandProfileDB(brand_id=brand.id, name=f"{TAG} Deutsch", language="de"))
    db.commit()
    record = create_content(db, title=f"Lisbon {TAG}", description="Three days", content=dict(ORIGINAL),
                            brand_id=brand.id)
    city = create_category(db, name=f"{TAG} City")
    assign_category_to_content(db, content_id=record.id, category_id=city.id, score=8, brand_id=brand.id)
    ai_service.publish_prompt(db, content_translate.TASK_KEY, content_translate.DEFAULT_PROMPT)
    return {"brand": brand, "record": record, "city": city}


@pytest.fixture
def model(monkeypatch):
    state = {"reply": "", "calls": [], "prompts": []}

    def provider(name=None, model=None):
        state["calls"].append(name)
        provider = MockAIProvider(canned_response=state["reply"])
        original = provider.generate

        def generate(prompt, max_output_tokens, system=None):
            state["prompts"].append(prompt)
            return original(prompt, max_output_tokens, system)

        provider.generate = generate
        return provider

    monkeypatch.setattr(ai_service, "get_ai_provider", provider)
    return state


GERMAN = {
    "title": f"Lissabon {TAG}",
    "description": "Drei Tage",
    "headline_medium": "Drei Tage in Lissabon",
    "body_medium": "Hallo {{salutation_informal}}, fahr mit **Tram 28** an [den Fliesen](https://example.invalid/tiles) vorbei.",
    "button_label": "Weiterlesen",
    "image_alt": "Eine gelbe Straßenbahn",
}


def _reply(**changes):
    return "```json\n" + json.dumps({**GERMAN, **changes}, ensure_ascii=False) + "\n```"


def _set_language(client, csrf, record_id, language):
    return client.patch(f"/content/{record_id}", json={"language": language}, headers={"X-CSRF-Token": csrf})


def _translate(client, csrf, record_id, language="de"):
    return client.post(f"/content/{record_id}/translations", json={"language": language},
                       headers={"X-CSRF-Token": csrf})


# --- a record's language (ADR-200 point 1) -------------------------------------------

def test_a_language_is_one_of_the_brands_profile_languages_or_not_set(db, world):
    record = world["record"]
    with signed_in(db) as (client, _token, csrf):
        refused = _set_language(client, csrf, record.id, "fr")
        chosen = _set_language(client, csrf, record.id, "en")
        detail = client.get(f"/content/{record.id}").json()
        cleared = _set_language(client, csrf, record.id, None)
    assert refused.status_code == 422 and "language" in refused.text
    assert chosen.status_code == 200 and detail["language"] == "en"
    assert {"de", "en"} <= set(detail["language_choices"])
    assert cleared.status_code == 200 and cleared.json()["language"] is None


def test_an_edit_that_does_not_name_the_language_leaves_it(db, world):
    record = world["record"]
    with signed_in(db) as (client, _token, csrf):
        _set_language(client, csrf, record.id, "en")
        client.patch(f"/content/{record.id}", json={"title": f"Lisbon again {TAG}"}, headers={"X-CSRF-Token": csrf})
        assert client.get(f"/content/{record.id}").json()["language"] == "en"


# --- slots match the variant's language (point 2) ------------------------------------

def test_a_slot_picks_only_its_variants_language_or_none(db, world):
    from app.campaigns.db_models import DecisionSlotDB, VariantDB
    from app.campaigns.service import create_campaign, create_decision_slot_for_variant, create_module_for_variant
    from app.content.service import create_content_version, mark_ready
    from app.decision.strategies.base import candidate_query

    brand = world["brand"]
    ids = {}
    for language in (None, "en", "de"):
        r = create_content(db, title=f"slot {language} {TAG}", content=dict(ORIGINAL), brand_id=brand.id)
        db.query(ContentRecordDB).filter_by(id=r.id).update({"language": language, "machine_ready": True})
        db.commit()
        create_content_version(db, content_record_id=r.id, created_by="test", brand_id=brand.id)
        mark_ready(db, r.id, "email", marked_by="test", brand_id=brand.id)
        # A slot draws on categorised records.
        assign_category_to_content(db, content_id=r.id, category_id=world["city"].id, score=5, brand_id=brand.id)
        ids[language] = r.id
    campaign = create_campaign(db, name=f"{TAG} slots", brand_id=brand.id, channel="email")
    variant = db.query(VariantDB).filter_by(campaign_id=campaign.id).one()
    slot = create_decision_slot_for_variant(db, variant_id=variant.id, name=f"{TAG}", brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="img_left", decision_slot_id=slot.id,
                              brand_id=brand.id)
    try:
        picked = {row[0].id for row in candidate_query(db, slot, brand_id=brand.id).all()}
        assert ids[None] in picked and ids["en"] in picked and ids["de"] not in picked
        german = db.query(BrandProfileDB).filter_by(name=f"{TAG} Deutsch").one()
        variant.brand_profile_id = german.id
        db.commit()
        picked = {row[0].id for row in candidate_query(db, slot, brand_id=brand.id).all()}
        assert ids[None] in picked and ids["de"] in picked and ids["en"] not in picked
    finally:
        from app.campaigns.db_models import CampaignDB, ModuleInstanceDB

        db.rollback()
        db.query(ModuleInstanceDB).filter_by(variant_id=variant.id).delete()
        db.query(DecisionSlotDB).filter_by(id=slot.id).delete()
        db.query(VariantDB).filter_by(id=variant.id).delete()
        db.query(CampaignDB).filter_by(id=campaign.id).delete()
        db.commit()


# --- translating (points 3 and 4) -----------------------------------------------------

def test_a_translation_is_a_new_linked_record_holding_only_what_a_person_must_still_decide(db, world, model):
    record = world["record"]
    model["reply"] = _reply()
    with signed_in(db) as (client, _token, csrf):
        _set_language(client, csrf, record.id, "en")
        response = _translate(client, csrf, record.id)
        assert response.status_code == 201, response.text
        twin_id = response.json()["record_id"]
        detail = client.get(f"/content/{twin_id}").json()
        original = client.get(f"/content/{record.id}").json()
    twin = db.get(ContentRecordDB, twin_id)
    assert (twin.brand_id, twin.language, twin.translation_of_id) == (world["brand"].id, "de", record.id)
    assert twin.title == f"Lissabon {TAG}" and twin.description == "Drei Tage"
    assert twin.content["headline_medium"] == "Drei Tage in Lissabon"
    assert twin.content["image_alt"] == "Eine gelbe Straßenbahn"
    # Links and images copied unchanged.
    assert twin.content["button_url"] == ORIGINAL["button_url"] and twin.content["image_url"] == ORIGINAL["image_url"]
    # Nothing a person must decide comes along.
    assert twin.machine_ready is False and twin.status == record.status
    assert db.query(ContentChannelReadinessDB).filter_by(content_id=twin_id).count() == 0
    [copied] = db.query(ContentCategoryAssignmentDB).filter_by(content_id=twin_id).all()
    assert (copied.category_id, copied.score) == (world["city"].id, 8)
    assert detail["original"]["id"] == record.id and detail["original_changed"] == []
    assert [t["language"] for t in original["translations"]] == ["de"]
    # The model was told the target language and given the record's own text, never a link to change.
    assert "German" in model["prompts"][0] and "Three days in Lisbon" in model["prompts"][0]
    [entry] = db.query(AuditEventDB).filter_by(action="content.created", subject_type="content",
                                               subject_id=twin_id).all()
    assert entry.detail["translation_of"] == record.id and entry.detail["ai_run_id"] == response.json()["ai_run_id"]


def test_a_changed_placeholder_or_link_keeps_the_original_text_and_says_so(db, world, model):
    record = world["record"]
    model["reply"] = _reply(body_medium="Hallo {{first_name}}, fahr [hier](https://elsewhere.invalid).")
    with signed_in(db) as (client, _token, csrf):
        _set_language(client, csrf, record.id, "en")
        response = _translate(client, csrf, record.id)
    twin = db.get(ContentRecordDB, response.json()["record_id"])
    assert twin.content["body_medium"] == ORIGINAL["body_medium"]
    assert any("body_medium" in n for n in response.json()["notices"])
    # Kept in the original's words, so it counts as still to be translated.
    with signed_in(db) as (client, _token, _csrf):
        assert "body_medium" in client.get(f"/content/{twin.id}").json()["original_changed"]


@pytest.mark.parametrize("setup, language, field", [
    ("unset", "de", "language"),        # the original's own language first
    ("en", "en", "language"),           # not into its own
    ("en", "fr", "language"),           # only a profile language
])
def test_refused_before_any_call(db, world, model, setup, language, field):
    record = world["record"]
    with signed_in(db) as (client, _token, csrf):
        if setup != "unset":
            _set_language(client, csrf, record.id, setup)
        response = _translate(client, csrf, record.id, language)
    assert response.status_code == 422 and field in json.dumps(response.json()["detail"])
    assert model["calls"] == []


def test_one_translation_per_language_and_none_of_a_translation(db, world, model):
    record = world["record"]
    model["reply"] = _reply()
    with signed_in(db) as (client, _token, csrf):
        _set_language(client, csrf, record.id, "en")
        twin_id = _translate(client, csrf, record.id).json()["record_id"]
        again = _translate(client, csrf, record.id)
        of_twin = _translate(client, csrf, twin_id, "en")
    assert again.status_code == 409 and str(twin_id) in again.text
    assert of_twin.status_code == 409
    assert len(model["calls"]) == 1


def test_a_linked_records_language_is_locked(db, world, model):
    record = world["record"]
    model["reply"] = _reply()
    with signed_in(db) as (client, _token, csrf):
        _set_language(client, csrf, record.id, "en")
        twin_id = _translate(client, csrf, record.id).json()["record_id"]
        on_original = _set_language(client, csrf, record.id, "de")
        on_twin = _set_language(client, csrf, twin_id, None)
        detail = client.get(f"/content/{record.id}").json()
    assert on_original.status_code == on_twin.status_code == 422
    assert detail["language_locked"]


def test_translating_needs_content_manage_as_well_as_ai_run(db, world, model):
    from app.auth.permissions import AI_RUN, VIEW
    from tests.test_brand_profile_api import person_with

    record = world["record"]
    db.query(ContentRecordDB).filter_by(id=record.id).update({"language": "en"})
    db.commit()
    with person_with(db, [VIEW, AI_RUN]) as (client, headers):
        response = client.post(f"/content/{record.id}/translations", json={"language": "de"}, headers=headers)
    assert response.status_code == 403
    assert model["calls"] == []


def test_the_translate_route_costs_ai_run():
    from app.auth.permissions import AI_RUN
    from app.auth.policy import required_permission

    assert required_permission("POST", "/content/{content_id}/translations") == AI_RUN
    assert required_permission("POST", "/content/{content_id}/retranslations") == AI_RUN


# --- staying honest (point 5) ---------------------------------------------------------

def test_a_changed_original_shows_per_field_and_taking_a_fresh_translation_clears_it(db, world, model):
    record = world["record"]
    model["reply"] = _reply()
    with signed_in(db) as (client, _token, csrf):
        h = {"X-CSRF-Token": csrf}
        _set_language(client, csrf, record.id, "en")
        twin_id = _translate(client, csrf, record.id).json()["record_id"]
        twin_version = client.get(f"/content/{twin_id}").json()
        client.patch(f"/content/{record.id}", json={"content": {"headline_medium": "Four days in Lisbon"},
                                                   "groups": ["email"]}, headers=h)
        # A change that is not text does not count.
        db.query(ContentRecordDB).filter_by(id=record.id).update({"machine_ready": True})
        db.commit()
        assert client.get(f"/content/{twin_id}").json()["original_changed"] == ["headline_medium"]

        model["reply"] = _reply(headline_medium="Vier Tage in Lissabon")
        run = client.post(f"/content/{twin_id}/retranslations", headers=h)
        assert run.status_code == 200, run.text
        [proposal] = client.get(f"/content/{twin_id}/retranslations").json()
        fields = {f["name"]: f for f in proposal["fields"]}
        assert fields["headline_medium"]["text"] == "Vier Tage in Lissabon"
        assert fields["headline_medium"]["current"] == "Drei Tage in Lissabon"
        assert proposal["categories"] == []
        # Nothing was written by asking.
        assert db.get(ContentRecordDB, twin_id).content["headline_medium"] == "Drei Tage in Lissabon"

        taken = client.patch(f"/content/{twin_id}", json={
            "content": {"headline_medium": "Vier Tage in Lissabon"}, "groups": ["email"],
            "applied_suggestion_run_id": run.json()["ai_run_id"]}, headers=h)
        assert taken.status_code == 200, taken.text
        after = client.get(f"/content/{twin_id}").json()
        # Marking it taken keeps the version the save answered with, so the next save is not refused.
        assert after["updated_at"] == taken.json()["updated_at"]
    assert twin_version["original_changed"] == []
    assert after["original_changed"] == []
    [entry] = (db.query(AuditEventDB).filter_by(action="content.updated", subject_type="content", subject_id=twin_id)
               .all())
    assert entry.detail["ai_run_id"] == run.json()["ai_run_id"]


def test_taking_a_run_of_another_record_marks_nothing_up_to_date(db, world, model):
    record = world["record"]
    model["reply"] = _reply()
    with signed_in(db) as (client, _token, csrf):
        h = {"X-CSRF-Token": csrf}
        _set_language(client, csrf, record.id, "en")
        twin_id = _translate(client, csrf, record.id).json()["record_id"]
        client.patch(f"/content/{record.id}", json={"content": {"headline_medium": "Four days"},
                                                   "groups": ["email"]}, headers=h)
        stray = AIRunDB(task_key=content_translate.TASK_KEY, provider="mock", status="ok", target_type="content",
                        target_id=record.id, output_text="{}", input_snapshot={"headline_medium": "Four days"})
        db.add(stray)
        db.commit()
        client.patch(f"/content/{twin_id}", json={"content": {"headline_medium": "Vier Tage"}, "groups": ["email"],
                                                  "applied_suggestion_run_id": stray.id}, headers=h)
        assert client.get(f"/content/{twin_id}").json()["original_changed"] == ["headline_medium"]


def test_deleting_the_original_leaves_the_translation_standing(db, world, model):
    record = world["record"]
    model["reply"] = _reply()
    with signed_in(db) as (client, _token, csrf):
        _set_language(client, csrf, record.id, "en")
        twin_id = _translate(client, csrf, record.id).json()["record_id"]
        deleted = client.delete(f"/content/{record.id}?force=true", headers={"X-CSRF-Token": csrf})
        detail = client.get(f"/content/{twin_id}")
    assert deleted.status_code in (200, 204), deleted.text
    assert detail.status_code == 200 and detail.json()["original"] is None


def test_the_task_offers_no_approval_step():
    from app.ai.tasks.registry import get_task

    assert get_task(content_translate.TASK_KEY).held_form is False
