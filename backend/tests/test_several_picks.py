"""A decision slot shows up to N picks (task-109; ADR-084 addendum 2026-10-11).

Decided with the user 2026-10-11, one question at a time:
  - several picks render by repeating the slot's module, best first; fewer
    found, fewer shown; none hides it (ADR-086);
  - "show up to" is 1-5 and editable; a push slot is always 1; no minimum;
  - no article twice in one email between slots: slots resolve in module
    order and a later slot takes its next ranked candidates. Hand-bound versus
    slot stays task-220.
The shape (rank and pick_set on resolution rows, strategies that rank) is the
final-design pass's, recorded in the same addendum.
"""
import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.campaigns.db_models import DecisionResolutionDB, DecisionSlotDB, ModuleInstanceDB
from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB, ContentChannelReadinessDB, ContentRecordDB
from app.content.service import create_content, create_content_version
from app.decision import sets
from app.decision.service import execute_decision_slot as real_execute
from app.decision.strategies.registry import get_strategy
from app.delivery.db_models import DeliveryExecutionDB
from app.delivery.service import reconstruct_delivery
from tests import test_render_skip as fixtures
from tests.test_api_guard import signed_in

db = fixtures.db
world = fixtures.world
api = TestClient(__import__("main").app, raise_server_exceptions=False)


@pytest.fixture
def catalogue(db, world, monkeypatch):
    """`catalogue(scores, channel)` makes a fresh category with one ready,
    published record per score, and returns (category id, [record ids])."""
    monkeypatch.setattr("app.decision.service.execute_decision_slot", real_execute)
    brand = world["brand"]
    categories: list[int] = []

    def make(scores, channel="email", category_id=None):
        if category_id is None:
            category = CategoryDB(name=f"picks-{uuid.uuid4().hex[:8]}", type="main")
            db.add(category)
            db.flush()
            categories.append(category.id)
            category_id = category.id
        ids = []
        for score in scores:
            record = create_content(db, title=f"picks-{score}-{uuid.uuid4().hex[:4]}", brand_id=brand.id, content={
                "headline_medium": f"Headline {score}", "body_medium": "Body", "button_label": "Read",
                "button_url": f"https://example.com/{score}", "push_title": f"Title {score}", "push_body": "B"})
            create_content_version(db, content_record_id=record.id, created_by="test", brand_id=brand.id)
            world["made"]["records"].append(record.id)
            row = db.get(ContentRecordDB, record.id)
            row.machine_ready = True
            db.add(ContentCategoryAssignmentDB(content_id=record.id, category_id=category_id, score=score))
            db.add(ContentChannelReadinessDB(content_id=record.id, channel=channel, marked_by="test"))
            ids.append(record.id)
        db.commit()
        return category_id, ids

    yield make
    db.rollback()
    records = world["made"]["records"]
    db.query(ContentChannelReadinessDB).filter(ContentChannelReadinessDB.content_id.in_(records)).delete(
        synchronize_session=False)
    db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.content_id.in_(records)).delete(
        synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id.in_(categories)).delete(synchronize_session=False)
    db.commit()


def _slots(db, variant):
    return (db.query(DecisionSlotDB).join(ModuleInstanceDB, ModuleInstanceDB.decision_slot_id == DecisionSlotDB.id)
            .filter(ModuleInstanceDB.variant_id == variant.id).order_by(ModuleInstanceDB.position).all())


def _configure(db, slot, category_ids, up_to):
    slot.candidate_filter = {"category_ids": list(category_ids)}
    slot.max_results = up_to
    db.commit()


def _execution(db, person):
    db.expire_all()
    return (db.query(DeliveryExecutionDB).filter_by(recipient_id=person.id)
            .order_by(DeliveryExecutionDB.id.desc()).first())


def _picked(execution):
    return [(p["content_record_id"], p.get("rank")) for p in execution.delivery_record["picks"]]


# --- one slot, several picks ------------------------------------------------------------

def test_a_slot_shows_up_to_its_number_best_first(db, world, catalogue):
    category, (a, b, c, d) = catalogue([9, 7, 5, 3])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 3)
    person = world["person"]()
    _, rows = world["send"](variant, [person])
    assert rows[person.id] == ("sent", None)
    execution = _execution(db, person)
    assert _picked(execution) == [(a, 1), (b, 2), (c, 3)]

    rebuilt = reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)
    assert rebuilt["hash_matches"] is True
    body = rebuilt["body"]
    # The module is drawn once per pick, in rank order, each with its own content id.
    assert [int(i) for i in re.findall(r'data-content-id="(\d+)"', body)] == [a, b, c]
    assert body.index("Headline 9") < body.index("Headline 7") < body.index("Headline 5")
    assert "Headline 3" not in body
    for record_id in (a, b, c):
        assert f"nl_content={record_id}" in body, "each copy's links credit its own record"
    slot_modules = [m for m in rebuilt["modules"] if m["kind"] == "slot"]
    assert [(m["content_record_id"], m["rank"]) for m in slot_modules] == [(a, 1), (b, 2), (c, 3)]


def test_fewer_found_fewer_shown(db, world, catalogue):
    category, (a, b) = catalogue([5, 3])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 5)
    person = world["person"]()
    world["send"](variant, [person])
    assert _picked(_execution(db, person)) == [(a, 1), (b, 2)]


def test_one_set_is_stored_with_ranks(db, world, catalogue):
    category, (a, b, _c) = catalogue([7, 5, 3])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 2)
    person = world["person"]()
    world["send"](variant, [person])
    picked = sets.latest_pick_set(db, slot.id, person.id)
    assert [(r.content_record_id, r.rank) for r in picked] == [(a, 1), (b, 2)]
    assert len({r.pick_set for r in picked}) == 1 and picked[0].pick_set is not None


def test_a_record_in_two_categories_is_picked_once(db, world, catalogue):
    first, (a, b) = catalogue([9, 3])
    second, _ = catalogue([], category_id=None)
    db.add(ContentCategoryAssignmentDB(content_id=a, category_id=second, score=8))
    db.commit()
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [first, second], 3)
    picked = get_strategy("top_score").rank(db, slot, limit=3)
    assert [p.content_record_id for p in picked] == [a, b]


def test_the_strategy_skips_what_is_excluded(db, world, catalogue):
    category, (a, b, c, d) = catalogue([9, 7, 5, 3])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 3)
    picked = get_strategy("top_score").rank(db, slot, limit=3, exclude=frozenset({b}))
    assert [p.content_record_id for p in picked] == [a, c, d]
    # The single-pick call is still the first of the ranking.
    assert get_strategy("top_score").execute(db, slot).content_record_id == a


def test_the_personal_strategy_ranks_by_its_combined_score(db, world, catalogue, monkeypatch):
    category, (a, b, c) = catalogue([7, 5, 3])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 2)
    slot.decision_strategy = "recipient_top_score"
    db.commit()
    person = world["person"]()
    monkeypatch.setattr("app.decision.strategies.recipient_top_score.operational_signals_for_recipient",
                        lambda db_, recipient_id: {category: 1.0})
    picked = get_strategy("recipient_top_score").rank(db, slot, recipient_id=person.id, limit=2)
    assert [p.content_record_id for p in picked] == [a, b]


def test_a_preview_for_the_recipient_shows_every_pick(db, world, catalogue):
    from app.rendering.service import render_variant_html

    category, (a, b, _c) = catalogue([7, 5, 3])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 2)
    person = world["person"]()
    world["send"](variant, [person])
    html = render_variant_html(db, variant.id, recipient_id=person.id)
    assert [int(i) for i in re.findall(r'data-content-id="(\d+)"', html)] == [a, b]


def test_a_row_from_before_is_a_set_of_one(db, world, catalogue):
    category, (a,) = catalogue([4])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    # Two rows from before sets: history, the newer one current.
    older = DecisionResolutionDB(decision_slot_id=slot.id, recipient_id=None, content_record_id=a)
    db.add(older)
    db.commit()
    legacy = DecisionResolutionDB(decision_slot_id=slot.id, recipient_id=None, content_record_id=a)
    db.add(legacy)
    db.commit()
    picked = sets.latest_pick_set(db, slot.id, None)
    assert [(r.id, r.rank, r.pick_set) for r in picked] == [(legacy.id, 1, None)]


def test_a_recorded_pick_from_before_ranks_still_rebuilds(db, world, catalogue):
    """A delivery record written before picks had a rank renders as it did."""
    from app.rendering.frame import render_frame
    from app.snapshots.service import create_snapshot_for_variant

    category, (a,) = catalogue([10])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 1)
    person = world["person"]()
    world["send"](variant, [person])
    execution = _execution(db, person)
    old_picks = [{k: v for k, v in p.items() if k != "rank"} for p in execution.delivery_record["picks"]]
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=world["brand"].id)
    world["made"]["snapshots"].append(snapshot.id)
    artifact, made = render_frame(db, snapshot.render_context, picks=old_picks)
    assert [int(i) for i in re.findall(r'data-content-id="(\d+)"', artifact.body)] == [a]


# --- between slots ------------------------------------------------------------------------

def test_a_later_slot_takes_its_next_picks_not_an_earlier_slots(db, world, catalogue):
    category, (a, b, c, d, _e) = catalogue([9, 8, 7, 6, 5])
    variant = world["variant"](slots=2)
    first, second = _slots(db, variant)
    _configure(db, first, [category], 2)
    _configure(db, second, [category], 2)
    person = world["person"]()
    world["send"](variant, [person])
    assert _picked(_execution(db, person)) == [(a, 1), (b, 2), (c, 1), (d, 2)]
    # The slot's global set is unchanged; this person has one of their own.
    assert [r.content_record_id for r in sets.latest_pick_set(db, second.id, None)] == [a, b]
    assert [r.content_record_id for r in sets.latest_pick_set(db, second.id, person.id)] == [c, d]


def test_an_exclusion_set_goes_once_the_overlap_does(db, world, catalogue):
    category, (a, b, c, d) = catalogue([9, 7, 5, 3])
    other, (x,) = catalogue([10])
    variant = world["variant"](slots=2)
    first, second = _slots(db, variant)
    _configure(db, first, [category], 2)
    _configure(db, second, [category], 2)
    person = world["person"]()
    world["send"](variant, [person])
    # The first slot now picks from elsewhere: no overlap, so the second slot's
    # current global set applies to this person again, not last time's own set.
    _configure(db, first, [other], 1)
    world["send"](variant, [person])
    assert _picked(_execution(db, person)) == [(x, 1), (a, 1), (b, 2)]
    assert sets.latest_pick_set(db, second.id, person.id)[0].recipient_id is None


# --- the setting --------------------------------------------------------------------------

def _slot_of(db, world, channel="email"):
    variant = world["variant"](channel, slots=1)
    return variant, _slots(db, variant)[0]


@pytest.mark.parametrize("value", [0, 6, -1])
def test_up_to_is_one_to_five(db, world, value):
    variant, slot = _slot_of(db, world)
    with signed_in(db) as (cookied, _token, csrf):
        patched = cookied.patch(f"/campaigns/decision-slots/{slot.id}", json={"max_results": value},
                                headers={"X-CSRF-Token": csrf})
        created = cookied.post(f"/campaigns/variants/{variant.id}/decision-slots",
                               json={"name": "x", "max_results": value}, headers={"X-CSRF-Token": csrf})
    assert patched.status_code == 422 and created.status_code == 422


def test_up_to_is_editable(db, world):
    _variant, slot = _slot_of(db, world)
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.patch(f"/campaigns/decision-slots/{slot.id}", json={"max_results": 3},
                                 headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200, response.text
    assert response.json()["max_results"] == 3
    db.refresh(slot)
    assert slot.max_results == 3


def test_patching_something_else_keeps_it(db, world):
    _variant, slot = _slot_of(db, world)
    slot.max_results = 4
    db.commit()
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.patch(f"/campaigns/decision-slots/{slot.id}", json={"candidate_filter": {}},
                                 headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200, response.text
    assert response.json()["max_results"] == 4


def test_a_push_slot_is_always_one(db, world):
    variant, slot = _slot_of(db, world, "push")
    with signed_in(db) as (cookied, _token, csrf):
        patched = cookied.patch(f"/campaigns/decision-slots/{slot.id}", json={"max_results": 2},
                                headers={"X-CSRF-Token": csrf})
        created = cookied.post(f"/campaigns/variants/{variant.id}/decision-slots",
                               json={"name": "x", "max_results": 2}, headers={"X-CSRF-Token": csrf})
    assert patched.status_code == 400 and "push" in patched.json()["detail"]
    assert created.status_code == 400
