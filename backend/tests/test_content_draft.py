"""The AI drafts a content record from a pasted source and proposes its
categories (task-368; ADR-141 addendum 2026-10-16, ADR-140 addendum of the
same date).

What these pin: the model is asked only for the text fields of the ticked
channels (never links, images or image descriptions) and only from the
existing categories; whatever it answers outside that is dropped and said; the
source is never kept; refusals cost nothing; taking a field or a category is an
ordinary write whose audit entry names the run; and the task offers no
approval step.
"""
import json
import uuid

import pytest
from sqlalchemy import text

from app.ai import service as ai_service
from app.ai.adapters.mock import MockAIProvider
from app.ai.db_models import AIPromptDB, AIRunDB
from app.ai.tasks import content_draft
from app.audit.db_models import AuditEventDB
from app.auth.service import ensure_default_brand
from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB
from app.content.service import create_category, create_content
from tests.test_api_guard import signed_in

TAG = f"t368-{uuid.uuid4().hex[:5]}"
SOURCE = f"{TAG} Lisbon in spring: trams, tiles, and pastel de nata on every corner."


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    yield session
    session.rollback()
    records = [r for (r,) in session.query(ContentRecordDB.id).filter(ContentRecordDB.title.like(f"{TAG}%"))]
    session.query(AuditEventDB).filter(AuditEventDB.subject_type == "content",
                                       AuditEventDB.subject_id.in_(records)).delete(synchronize_session=False)
    session.query(AIRunDB).filter(AIRunDB.task_key == content_draft.TASK_KEY).delete(synchronize_session=False)
    session.query(AIPromptDB).filter(AIPromptDB.task_key == content_draft.TASK_KEY).delete(synchronize_session=False)
    session.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.content_id.in_(records)).delete(synchronize_session=False)
    for rid in records:
        session.execute(text("DELETE FROM content_versions WHERE content_record_id = :r"), {"r": rid})
    session.query(ContentRecordDB).filter(ContentRecordDB.id.in_(records)).delete(synchronize_session=False)
    session.query(CategoryDB).filter(CategoryDB.name.like(f"{TAG}%")).delete(synchronize_session=False)
    session.commit()
    session.close()


@pytest.fixture
def world(db):
    brand = ensure_default_brand(db)
    record = create_content(db, title=f"{TAG} Lisbon", content={"headline_medium": "Already written"},
                            brand_id=brand.id)
    city = create_category(db, name=f"{TAG} City breaks")
    food = create_category(db, name=f"{TAG} Food")
    ai_service.publish_prompt(db, content_draft.TASK_KEY, content_draft.DEFAULT_PROMPT)
    return {"record": record, "city": city, "food": food}


def _reply(world, **extra):
    body = {
        "fields": {
            "headline_hero": "Lisbon in bloom",
            "headline_medium": "Three days in Lisbon",
            "body_medium": "Ride **tram 28** and see [the tiles](https://example.invalid/tiles).",
            "button_url": "https://invented.invalid",
            "image_alt": "A tram",
            "made_up_field": "x",
            "push_title": "Lisbon calls",
        },
        "categories": [
            {"name": f"{TAG} city breaks", "score": 9, "reason": "A short city trip."},
            {"name": f"{TAG} Food", "score": 14, "reason": "Out of range."},
            {"name": f"{TAG} Invented", "score": 5, "reason": "Not in the vocabulary."},
        ],
        **extra,
    }
    return "Here is the draft:\n```json\n" + json.dumps(body) + "\n```"


@pytest.fixture
def model(monkeypatch):
    """The provider the route reaches, answering with whatever a test sets."""
    calls = []

    def provider(name=None, model=None):
        calls.append(name)
        return MockAIProvider(canned_response=state["reply"])

    state = {"reply": "", "calls": calls}
    monkeypatch.setattr(ai_service, "get_ai_provider", provider)
    return state


def _draft(client, csrf, record_id, source=SOURCE, channels=("email",)):
    return client.post(f"/content/{record_id}/drafts", json={"source": source, "channels": list(channels)},
                       headers={"X-CSRF-Token": csrf})


# --- what the model is asked --------------------------------------------------------

def test_the_prompt_names_the_text_fields_of_the_ticked_channels_and_the_categories(db, world):
    prompt = content_draft.build_prompt(db, content_draft.DEFAULT_PROMPT, SOURCE, ["email"])
    for name in ("headline_hero", "headline_medium", "body_medium", "body_long", "button_label"):
        assert name in prompt
    for name in ("button_url", "image_url", "image_alt", "push_title"):
        assert name not in prompt
    assert "must be SHORT" in prompt          # a field's note goes along as guidance
    assert f"{TAG} City breaks" in prompt and SOURCE in prompt


# --- what is kept of the answer -----------------------------------------------------

def test_only_asked_for_fields_and_existing_categories_are_kept_and_the_rest_is_said(db, world):
    proposal = content_draft.read_proposal(db, _reply(world), ["email"])
    fields = {f["name"]: f["text"] for f in proposal["fields"]}
    assert fields == {
        "headline_hero": "Lisbon in bloom",
        "headline_medium": "Three days in Lisbon",
        # A link the model wrote is reduced to its label; bold stays.
        "body_medium": "Ride **tram 28** and see the tiles.",
    }
    [city] = proposal["categories"]
    assert (city["category_id"], city["score"], city["reason"]) == (world["city"].id, 9, "A short city trip.")
    notices = " ".join(proposal["notices"])
    assert "button_url" in notices and "made_up_field" in notices and "push_title" in notices
    assert f"{TAG} Invented" in notices and "1 to 10" in notices


def test_an_unreadable_reply_keeps_nothing_and_says_so(db, world):
    proposal = content_draft.read_proposal(db, "I would rather not.", ["email"])
    assert proposal["fields"] == [] and proposal["categories"] == []


# --- the routes ---------------------------------------------------------------------

def test_a_draft_is_run_for_the_record_and_read_back_without_its_source(db, world, model):
    model["reply"] = _reply(world)
    with signed_in(db) as (client, _token, csrf):
        response = _draft(client, csrf, world["record"].id)
        assert response.status_code == 200, response.text
        [draft] = client.get(f"/content/{world['record'].id}/drafts").json()
    run = db.get(AIRunDB, response.json()["ai_run_id"])
    assert (run.target_type, run.target_id, run.task_key) == ("content", world["record"].id, "content_draft")
    assert draft["run_id"] == run.id and draft["status"] == "ok"
    # Read back with every channel's text fields: which were ticked is not kept.
    assert {f["name"] for f in draft["fields"]} == {"headline_hero", "headline_medium", "body_medium", "push_title"}
    current = {f["name"]: f["current"] for f in draft["fields"]}
    assert current["headline_medium"] == "Already written" and current["headline_hero"] == ""
    assert draft["categories"][0]["assigned_score"] is None
    row = {c: getattr(run, c) for c in run.__table__.columns.keys()}
    assert not any(isinstance(v, str) and TAG in v and "pastel" in v for v in row.values())


@pytest.mark.parametrize("body, field", [
    ({"source": "   ", "channels": ["email"]}, "source"),
    ({"source": "x" * (content_draft.MAX_SOURCE_CHARS + 1), "channels": ["email"]}, "source"),
    ({"source": "A brief", "channels": []}, "channels"),
    ({"source": "A brief", "channels": ["fax"]}, "channels"),
])
def test_refused_before_any_call_on_the_field_at_fault(db, world, model, body, field):
    with signed_in(db) as (client, _token, csrf):
        response = client.post(f"/content/{world['record'].id}/drafts", json=body, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 422
    assert field in json.dumps(response.json()["detail"])
    assert model["calls"] == []


def test_another_brands_record_is_not_found(db, world, model):
    from app.auth.db_models import BrandDB

    brand = BrandDB(key=TAG, name=TAG)
    db.add(brand)
    db.commit()
    other = create_content(db, title=f"{TAG} elsewhere", content={}, brand_id=brand.id)
    try:
        with signed_in(db) as (client, _token, csrf):
            assert _draft(client, csrf, other.id).status_code == 404
            assert client.get(f"/content/{other.id}/drafts").status_code == 404
        assert model["calls"] == []
    finally:
        db.query(ContentRecordDB).filter_by(id=other.id).delete()
        db.query(BrandDB).filter_by(id=brand.id).delete()
        db.commit()


def test_the_draft_route_costs_ai_run():
    from app.auth.permissions import AI_RUN
    from app.auth.policy import required_permission

    assert required_permission("POST", "/content/{content_id}/drafts") == AI_RUN


# --- taking it ------------------------------------------------------------------------

def _entries(db, record_id, action):
    db.expire_all()
    return (db.query(AuditEventDB).filter_by(action=action, subject_type="content", subject_id=record_id)
            .order_by(AuditEventDB.id).all())


def _run_of(db, task_key, target_type, target_id):
    run = AIRunDB(task_key=task_key, provider="mock", status="ok", target_type=target_type,
                  target_id=target_id, output_text="{}")
    db.add(run)
    db.commit()
    return run


def test_taken_fields_and_categories_name_the_run(db, world):
    record = world["record"]
    run = _run_of(db, content_draft.TASK_KEY, "content", record.id)
    with signed_in(db) as (client, _token, csrf):
        h = {"X-CSRF-Token": csrf}
        patched = client.patch(f"/content/{record.id}", json={
            "content": {"headline_hero": "Lisbon in bloom"}, "groups": ["email"],
            "applied_suggestion_run_id": run.id}, headers=h)
        assigned = client.post(f"/content/{record.id}/categories", json={
            "category_id": world["city"].id, "score": 9, "applied_suggestion_run_id": run.id}, headers=h)
        rescored = client.patch(f"/content/{record.id}/assignments/{assigned.json()['id']}", json={
            "score": 7, "applied_suggestion_run_id": run.id}, headers=h)
    assert patched.status_code == assigned.status_code == rescored.status_code == 200
    for action in ("content.updated", "content.category_assigned", "content.category_score_changed"):
        [entry] = _entries(db, record.id, action)
        assert entry.detail["applied_suggestion"] is True and entry.detail["ai_run_id"] == run.id, action


@pytest.mark.parametrize("task_key, target_type, other_record", [
    ("subject_preheader", "content", False), ("content_draft", "variant", False), ("content_draft", "content", True)])
def test_a_run_of_another_task_or_another_record_is_not_named(db, world, task_key, target_type, other_record):
    record = world["record"]
    target = create_content(db, title=f"{TAG} other", content={}, brand_id=ensure_default_brand(db).id).id \
        if other_record else record.id
    run = _run_of(db, task_key, target_type, target)
    with signed_in(db) as (client, _token, csrf):
        client.patch(f"/content/{record.id}", json={"content": {"headline_hero": "Hi"}, "groups": ["email"],
                                                    "applied_suggestion_run_id": run.id},
                     headers={"X-CSRF-Token": csrf})
    [entry] = _entries(db, record.id, "content.updated")
    assert "applied_suggestion" not in entry.detail
    db.delete(run)
    db.commit()


# --- no approval step (ADR-140 addendum 2026-10-16) ----------------------------------

def test_the_task_offers_no_approval_step_and_settings_say_so(db, world):
    with signed_in(db) as (client, _token, csrf):
        refused = client.put("/settings/ai/tasks/content_draft/approval", json={"mode": "require_approval"},
                             headers={"X-CSRF-Token": csrf})
        tasks = {t["key"]: t for t in client.get("/settings").json()["ai_tasks"]}
    assert refused.status_code == 422 and "approval" in refused.text
    assert tasks["content_draft"]["held_form"] is False
    assert tasks["subject_preheader"]["held_form"] is True


def test_the_registry_finds_a_task_whose_file_sorts_before_its_own():
    """Discovery reloaded every module in the package, `base` and itself
    included: a task file sorting before "registry" was checked against the
    TaskMeta class the reload of `base` had just replaced, and vanished."""
    from app.ai.tasks import registry

    for _ in range(2):  # the first load, and a reload of what is loaded
        assert {"content_draft", "subject_preheader"} <= set(registry._discover())


def test_the_jinja_settings_card_shows_no_switch_for_it(db, world):
    with signed_in(db) as (client, _token, _csrf):
        page = client.get("/ui/settings").text
    card = page[page.index("AI task — Content draft"):page.index("AI task — Subject")]
    assert "No approval step" in card and 'name="mode"' not in card
    assert 'name="mode"' in page[page.index("AI task — Subject"):]
