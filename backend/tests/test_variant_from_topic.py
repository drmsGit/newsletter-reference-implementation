"""AI prepares a variant from a topic (task-370; ADR-141 addendum 2026-10-17).

What these pin: it is offered only for an empty email variant; the model
chooses only among what a slot may take (published, ready, machine ready, in
the variant's language or none), the newest first; whatever it answers
outside that offer is dropped and said; refusals cost nothing; and building
lays out the fixed shape — hero, editorial, alternating image blocks, the
slot — from the ticked parts only, rechecked, every entry naming the run.
"""
import json
import uuid

import pytest
from sqlalchemy import text

from app.ai import service as ai_service
from app.ai.adapters.mock import MockAIProvider
from app.ai.db_models import AIPromptDB, AIRunDB
from app.ai.tasks import variant_from_topic as task
from app.audit.db_models import AuditEventDB
from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign, create_module_for_variant
from app.rendering.service import envelope_fields_for_variant
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentChannelReadinessDB, ContentRecordDB,
)
from app.content.service import (
    assign_category_to_content, create_category, create_content, create_content_version, mark_ready,
)
from tests.test_api_guard import signed_in

TAG = f"t370-{uuid.uuid4().hex[:5]}"
BOTH = {"headline_hero": "Lisbon in bloom", "headline_medium": "Three days in Lisbon", "body_medium": "Trams.",
        "button_label": "Read", "button_url": "https://example.invalid/x"}
IMAGE_ONLY = {"headline_medium": "Porto by night", "body_medium": "Port wine.", "button_label": "Read",
              "button_url": "https://example.invalid/y"}


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    yield session
    session.rollback()
    records = [r for (r,) in session.query(ContentRecordDB.id).filter(ContentRecordDB.title.like(f"%{TAG}%"))]
    campaigns = [c for (c,) in session.query(CampaignDB.id).filter(CampaignDB.name.like(f"{TAG}%"))]
    variants = [v for (v,) in session.query(VariantDB.id).filter(VariantDB.campaign_id.in_(campaigns))]
    session.query(AuditEventDB).filter(
        ((AuditEventDB.subject_type == "content") & AuditEventDB.subject_id.in_(records))
        | ((AuditEventDB.subject_type == "variant") & AuditEventDB.subject_id.in_(variants))
    ).delete(synchronize_session=False)
    modules = [m for (m,) in session.query(ModuleInstanceDB.id).filter(ModuleInstanceDB.variant_id.in_(variants))]
    slots = [s for (s,) in session.query(DecisionSlotDB.id).filter(DecisionSlotDB.variant_id.in_(variants))]
    session.query(AuditEventDB).filter(
        ((AuditEventDB.subject_type == "module") & AuditEventDB.subject_id.in_(modules))
        | ((AuditEventDB.subject_type == "decision_slot") & AuditEventDB.subject_id.in_(slots))
    ).delete(synchronize_session=False)
    session.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variants)).delete(synchronize_session=False)
    session.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id.in_(variants)).delete(synchronize_session=False)
    session.query(VariantDB).filter(VariantDB.id.in_(variants)).delete(synchronize_session=False)
    session.query(CampaignDB).filter(CampaignDB.id.in_(campaigns)).delete(synchronize_session=False)
    session.query(AIRunDB).filter(AIRunDB.task_key == task.TASK_KEY).delete(synchronize_session=False)
    session.query(AIPromptDB).filter(AIPromptDB.task_key == task.TASK_KEY).delete(synchronize_session=False)
    for table, column in (("content_category_assignments", "content_id"), ("content_channel_readiness", "content_id"),
                          ("content_versions", "content_record_id")):
        session.execute(text(f"DELETE FROM {table} WHERE {column} = ANY(:r)"), {"r": records})
    session.query(ContentRecordDB).filter(ContentRecordDB.id.in_(records)).delete(synchronize_session=False)
    session.query(CategoryDB).filter(CategoryDB.name.like(f"{TAG}%")).delete(synchronize_session=False)
    session.commit()
    session.close()


def _record(db, brand, title, content, category, *, machine_ready=True, language=None, ready=True):
    r = create_content(db, title=f"{title} {TAG}", description=f"About {title}", content=dict(content),
                       brand_id=brand.id)
    db.query(ContentRecordDB).filter_by(id=r.id).update({"machine_ready": machine_ready, "language": language})
    db.commit()
    create_content_version(db, content_record_id=r.id, created_by="test", brand_id=brand.id)
    if ready:
        mark_ready(db, r.id, "email", marked_by="test", brand_id=brand.id)
    assign_category_to_content(db, content_id=r.id, category_id=category.id, score=7, brand_id=brand.id)
    return r.id


@pytest.fixture
def world(db):
    brand = ensure_default_brand(db)
    city = create_category(db, name=f"{TAG} City")
    food = create_category(db, name=f"{TAG} Food")
    ids = {
        "lisbon": _record(db, brand, "Lisbon", BOTH, city),
        "porto": _record(db, brand, "Porto", IMAGE_ONLY, food),
        "madrid": _record(db, brand, "Madrid", IMAGE_ONLY, city),
        "kept_back": _record(db, brand, "Kept back", BOTH, city, machine_ready=False),
        "german": _record(db, brand, "Berlin", BOTH, city, language="de"),
        "not_ready": _record(db, brand, "Rome", BOTH, city, ready=False),
    }
    campaign = create_campaign(db, name=f"{TAG} edition", brand_id=brand.id, channel="email")
    variant = db.query(VariantDB).filter_by(campaign_id=campaign.id).one()
    ai_service.publish_prompt(db, task.TASK_KEY, task.DEFAULT_PROMPT)
    return {"brand": brand, "ids": ids, "variant": variant, "city": city, "food": food}


@pytest.fixture
def model(monkeypatch):
    state = {"reply": "", "calls": 0, "prompts": []}

    def provider(name=None, model=None):
        state["calls"] += 1
        provider = MockAIProvider(canned_response=state["reply"])
        original = provider.generate

        def generate(prompt, max_output_tokens, system=None):
            state["prompts"].append(prompt)
            return original(prompt, max_output_tokens, system)

        provider.generate = generate
        return provider

    monkeypatch.setattr(ai_service, "get_ai_provider", provider)
    return state


def _reply(world, **changes):
    ids = world["ids"]
    body = {
        "hero": {"record_id": ids["lisbon"], "reason": "The topic's city."},
        "editorial": "Three cities for a **long weekend**.",
        "blocks": [{"record_id": ids["porto"], "reason": "Nearby."}, {"record_id": ids["madrid"], "reason": "Food."}],
        "slot": {"categories": [f"{TAG} City", f"{TAG} Food"], "reason": "Let each reader pick."},
        "subject": "A long weekend in Iberia", "preheader": "Lisbon, Porto, Madrid",
        **changes,
    }
    return json.dumps(body)


def _ask(client, csrf, variant_id, topic="City breaks in Iberia"):
    return client.post(f"/campaigns/variants/{variant_id}/topic-proposals", json={"topic": topic},
                       headers={"X-CSRF-Token": csrf})


# --- what the model is offered -------------------------------------------------------

def test_only_what_a_slot_may_take_is_offered_with_the_blocks_each_can_fill(db, world, model):
    ids = world["ids"]
    model["reply"] = _reply(world)
    with signed_in(db) as (client, _token, csrf):
        assert _ask(client, csrf, world["variant"].id).status_code == 200
    [prompt] = model["prompts"]
    assert f"id {ids['lisbon']}:" in prompt and f"id {ids['porto']}:" in prompt
    for kept_out in ("kept_back", "german", "not_ready"):
        assert f"id {ids[kept_out]}:" not in prompt, kept_out
    lisbon_line = next(line for line in prompt.splitlines() if f"id {ids['lisbon']}:" in line)
    porto_line = next(line for line in prompt.splitlines() if f"id {ids['porto']}:" in line)
    assert "hero" in lisbon_line and "image block" in lisbon_line and f"{TAG} City" in lisbon_line
    assert "hero" not in porto_line
    assert "City breaks in Iberia" in prompt and f"{TAG} Food" in prompt


def test_the_newest_are_offered_first_and_only_so_many(db, world, monkeypatch):
    monkeypatch.setattr(task, "OFFER_LIMIT", 2)
    offered = task.offer(db, world["variant"], world["brand"].id)
    assert sorted(int(i) for i in offered) == sorted([world["ids"]["porto"], world["ids"]["madrid"]])
    # The build's recheck reads the records named, however old.
    assert set(task.offer(db, world["variant"], world["brand"].id, only=[world["ids"]["lisbon"]])) == {
        str(world["ids"]["lisbon"])}


def test_too_little_to_choose_from_is_refused_before_the_call(db, world, model, monkeypatch):
    monkeypatch.setattr(task, "OFFER_LIMIT", 2)   # the two newest fill no hero
    with signed_in(db) as (client, _token, csrf):
        response = _ask(client, csrf, world["variant"].id)
    assert response.status_code == 409 and "hero" in response.text
    assert model["calls"] == 0


# --- what is kept of the answer --------------------------------------------------------

def test_what_lies_outside_the_offer_is_dropped_and_said(db, world, model):
    ids = world["ids"]
    model["reply"] = _reply(world, hero={"record_id": ids["porto"], "reason": "Cannot be a hero."},
                            blocks=[{"record_id": ids["madrid"], "reason": "ok"},
                                    {"record_id": ids["madrid"], "reason": "twice"},
                                    {"record_id": ids["kept_back"], "reason": "not offered"},
                                    {"record_id": 999999, "reason": "made up"}],
                            slot={"categories": [f"{TAG} City", "Nightlife on Mars"], "reason": "r"})
    with signed_in(db) as (client, _token, csrf):
        _ask(client, csrf, world["variant"].id)
        [proposal] = client.get(f"/campaigns/variants/{world['variant'].id}/topic-proposals").json()
    assert proposal["hero"] is None
    assert [b["record_id"] for b in proposal["blocks"]] == [ids["madrid"]]
    assert proposal["slot"]["category_ids"] == [world["city"].id]
    notices = " ".join(proposal["notices"]).lower()
    assert "cannot fill a hero" in notices and "more than once" in notices
    assert "nightlife on mars" in notices and "not offered" in notices


def test_a_proposal_is_read_back_with_titles_and_the_topic_is_not_kept(db, world, model):
    ids = world["ids"]
    model["reply"] = _reply(world)
    with signed_in(db) as (client, _token, csrf):
        run_id = _ask(client, csrf, world["variant"].id).json()["ai_run_id"]
        [proposal] = client.get(f"/campaigns/variants/{world['variant'].id}/topic-proposals").json()
    assert proposal["run_id"] == run_id
    assert proposal["hero"]["record_id"] == ids["lisbon"] and proposal["hero"]["title"].startswith("Lisbon")
    assert proposal["editorial"] == "Three cities for a **long weekend**."
    assert [b["title"].split()[0] for b in proposal["blocks"]] == ["Porto", "Madrid"]
    assert proposal["subject"] == "A long weekend in Iberia" and proposal["preheader"] == "Lisbon, Porto, Madrid"
    run = db.get(AIRunDB, run_id)
    assert "Iberia" not in json.dumps(run.input_snapshot)


# --- refused before the call -----------------------------------------------------------

@pytest.mark.parametrize("topic", ["   ", "x" * 501])
def test_an_empty_or_long_topic_is_refused_on_the_field(db, world, model, topic):
    with signed_in(db) as (client, _token, csrf):
        response = _ask(client, csrf, world["variant"].id, topic)
    assert response.status_code == 422 and "topic" in json.dumps(response.json()["detail"])
    assert model["calls"] == 0


def test_a_variant_with_content_blocks_is_refused(db, world, model):
    create_module_for_variant(db, variant_id=world["variant"].id, module_type="editorial",
                              module_data={"text": "Mine"}, brand_id=world["brand"].id)
    with signed_in(db) as (client, _token, csrf):
        response = _ask(client, csrf, world["variant"].id)
    assert response.status_code == 409 and "empty" in response.text
    assert model["calls"] == 0


def test_a_push_variant_is_refused(db, world, model):
    campaign = create_campaign(db, name=f"{TAG} push", brand_id=world["brand"].id, channel="push")
    variant = db.query(VariantDB).filter_by(campaign_id=campaign.id).one()
    with signed_in(db) as (client, _token, csrf):
        response = _ask(client, csrf, variant.id)
    assert response.status_code == 409 and "email" in response.text
    assert model["calls"] == 0


def test_the_route_costs_ai_run_and_the_task_has_no_approval_step():
    from app.ai.tasks.registry import get_task
    from app.auth.permissions import AI_RUN
    from app.auth.policy import required_permission

    assert required_permission("POST", "/campaigns/variants/{variant_id}/topic-proposals") == AI_RUN
    assert get_task(task.TASK_KEY).held_form is False


# --- building -----------------------------------------------------------------------------

def _build(client, csrf, variant_id, run_id, **choice):
    body = {"run_id": run_id, "hero": True, "editorial": None, "blocks": None, "slot": True, "envelope": True,
            **choice}
    return client.post(f"/campaigns/variants/{variant_id}/build-from-proposal", json=body,
                       headers={"X-CSRF-Token": csrf})


def _stack(db, variant_id):
    db.expire_all()
    return [(m.module_type, m.content_record_id, m.decision_slot_id, m.module_data)
            for m in db.query(ModuleInstanceDB).filter_by(variant_id=variant_id).order_by(ModuleInstanceDB.position)]


def test_building_lays_out_the_fixed_shape_and_names_the_run(db, world, model):
    ids, variant = world["ids"], world["variant"]
    model["reply"] = _reply(world)
    with signed_in(db) as (client, _token, csrf):
        run_id = _ask(client, csrf, variant.id).json()["ai_run_id"]
        built = _build(client, csrf, variant.id, run_id, editorial="Three cities, edited.")
    assert built.status_code == 200, built.text
    stack = [s for s in _stack(db, variant.id) if s[0] != "envelope"]
    assert [s[0] for s in stack] == ["hero", "editorial", "img_left", "img_right", "img_left"]
    assert [s[1] for s in stack[:4]] == [ids["lisbon"], None, ids["porto"], ids["madrid"]]
    assert stack[1][3] == {"text": "Three cities, edited."}
    slot = db.get(DecisionSlotDB, stack[4][2])
    assert slot.candidate_filter["category_ids"] == [world["city"].id, world["food"].id] and slot.max_results == 3
    assert envelope_fields_for_variant(db, variant.id, "email") == {"subject": "A long weekend in Iberia",
                                                           "preheader": "Lisbon, Porto, Madrid"}
    entries = db.query(AuditEventDB).filter(AuditEventDB.action.in_(["module.created", "decision_slot.created",
                                                                      "variant.updated"])).all()
    named = [e for e in entries if (e.detail or {}).get("ai_run_id") == run_id]
    assert len(named) == 7  # five modules, the slot, the envelope


def test_only_the_ticked_parts_are_built(db, world, model):
    ids, variant = world["ids"], world["variant"]
    model["reply"] = _reply(world)
    with signed_in(db) as (client, _token, csrf):
        run_id = _ask(client, csrf, variant.id).json()["ai_run_id"]
        built = _build(client, csrf, variant.id, run_id, hero=False, blocks=[ids["madrid"]], slot=False,
                       envelope=False, editorial="")
    assert built.status_code == 200, built.text
    assert [(s[0], s[1]) for s in _stack(db, variant.id) if s[0] != "envelope"] == [("img_left", ids["madrid"])]
    assert envelope_fields_for_variant(db, variant.id, "email").get("subject") in (None, "")


@pytest.mark.parametrize("change", ["filled", "kept_back", "foreign_block"])
def test_building_rechecks_and_refuses_without_building_anything(db, world, model, change):
    ids, variant = world["ids"], world["variant"]
    model["reply"] = _reply(world)
    with signed_in(db) as (client, _token, csrf):
        run_id = _ask(client, csrf, variant.id).json()["ai_run_id"]
        choice = {}
        if change == "filled":
            create_module_for_variant(db, variant_id=variant.id, module_type="editorial",
                                      module_data={"text": "Somebody wrote first"}, brand_id=world["brand"].id)
        elif change == "kept_back":
            db.query(ContentRecordDB).filter_by(id=ids["porto"]).update({"machine_ready": False})
            db.commit()
        else:
            # Takeable and image-capable, but the proposal put it in no block (it is the hero).
            choice = {"blocks": [ids["lisbon"]]}
        before = _stack(db, variant.id)
        built = _build(client, csrf, variant.id, run_id, **choice)
    assert built.status_code == (422 if change == "foreign_block" else 409), built.text
    assert _stack(db, variant.id) == before


def test_a_run_of_another_variant_builds_nothing(db, world, model):
    model["reply"] = _reply(world)
    other = create_campaign(db, name=f"{TAG} other", brand_id=world["brand"].id, channel="email")
    other_variant = db.query(VariantDB).filter_by(campaign_id=other.id).one()
    with signed_in(db) as (client, _token, csrf):
        run_id = _ask(client, csrf, other_variant.id).json()["ai_run_id"]
        built = _build(client, csrf, world["variant"].id, run_id)
    assert built.status_code == 404


def test_at_most_four_image_blocks_are_kept(db, world, model):
    brand, ids = world["brand"], world["ids"]
    extra = [_record(db, brand, f"Extra{n}", IMAGE_ONLY, world["city"]) for n in range(3)]
    model["reply"] = _reply(world, blocks=[{"record_id": i, "reason": "r"} for i in
                                           [ids["porto"], ids["madrid"], *extra]])
    with signed_in(db) as (client, _token, csrf):
        _ask(client, csrf, world["variant"].id)
        [proposal] = client.get(f"/campaigns/variants/{world['variant'].id}/topic-proposals").json()
    assert len(proposal["blocks"]) == 4


def test_a_visible_header_and_footer_do_not_count_as_content(db, world, model):
    for decorative in ("header", "footer"):
        create_module_for_variant(db, variant_id=world["variant"].id, module_type=decorative,
                                  brand_id=world["brand"].id)
    model["reply"] = _reply(world)
    with signed_in(db) as (client, _token, csrf):
        assert _ask(client, csrf, world["variant"].id).status_code == 200


def test_the_composition_says_when_it_is_offered(db, world):
    variant = world["variant"]
    push = create_campaign(db, name=f"{TAG} push offer", brand_id=world["brand"].id, channel="push")

    def offered(campaign_id, variant_id):
        with signed_in(db) as (client, _token, _csrf):
            composition = client.get(f"/campaigns/{campaign_id}/composition").json()
        return next(v for v in composition["variants"] if v["variant"]["id"] == variant_id)["preparable_from_topic"]

    assert offered(variant.campaign_id, variant.id) is True
    push_variant = db.query(VariantDB).filter_by(campaign_id=push.id).one()
    assert offered(push.id, push_variant.id) is False
    create_module_for_variant(db, variant_id=variant.id, module_type="editorial", module_data={"text": "Mine"},
                              brand_id=world["brand"].id)
    assert offered(variant.campaign_id, variant.id) is False


def test_a_subject_the_envelope_refuses_builds_nothing(db, world, model):
    """task-389: the envelope's own check (ADR-199) comes before any write."""
    variant = world["variant"]
    model["reply"] = _reply(world, subject="Hello {{t389_nobody_has_this}}")
    with signed_in(db) as (client, _token, csrf):
        run_id = _ask(client, csrf, variant.id).json()["ai_run_id"]
        before = _stack(db, variant.id)
        built = _build(client, csrf, variant.id, run_id)
    assert built.status_code == 422, built.text
    assert _stack(db, variant.id) == before
