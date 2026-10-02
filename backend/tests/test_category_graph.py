"""The category graph is one brand's, in every figure at once (task-57, ADR-150).

Built to fail on each half-scoping ADR-150's addendum warned against: a
content count that is brand-scoped beside a signal figure that still sums
every brand puts two populations on one canvas.

The audience is "latest marketing consent for this brand is opted in on any
registered channel" (decided 2026-10-02), so a push-only subscriber counts and
a person who consented only to another brand does not. Distinct weights per
person make a total say exactly who was summed.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import service as auth
from app.campaigns.db_models import DecisionResolutionDB, DecisionSlotDB
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB,
)
from app.database import SessionLocal
from app.insight.graph import category_graph
from app.recipients.consent import record_consent
from app.recipients.db_models import ConsentEventDB, RecipientDB, SignalContributionDB


@pytest.fixture
def world(db, default_brand, temp_brand):
    """One category; content and people in two brands; everything removed after."""
    other = temp_brand("graph")
    category = CategoryDB(name=f"graph-{uuid.uuid4().hex[:8]}", type="main")
    db.add(category)
    db.flush()

    def content(brand):
        record = ContentRecordDB(title=f"graph-{uuid.uuid4().hex[:6]}", content={},
                                 status="active", brand_id=brand.id)
        db.add(record)
        db.flush()
        db.add(ContentCategoryAssignmentDB(content_id=record.id, category_id=category.id, score=1))
        return record

    ours, theirs = content(default_brand), content(other)

    def person(weight, consents):
        recipient = RecipientDB(external_id=f"graph-{uuid.uuid4()}", status="active")
        db.add(recipient)
        db.flush()
        for brand, channel in consents:
            record_consent(db, recipient.id, "opted_in", brand.id, channel=channel,
                           source="test", note="graph", commit=False, purpose="marketing")
        db.add(SignalContributionDB(recipient_id=recipient.id, category_id=category.id,
                                    contribution_type="manual", base_weight=weight))
        return recipient

    people = [
        person(1.0, [(default_brand, "email")]),   # in our audience by email
        person(2.0, [(default_brand, "push")]),    # in it by push only
        person(4.0, [(other, "email")]),           # only the other brand's
        person(8.0, []),                           # nobody's
    ]

    slot = db.query(DecisionSlotDB).order_by(DecisionSlotDB.id).first()
    assert slot is not None, "the seed left no decision slot to hang a resolution on"
    db.add(DecisionResolutionDB(decision_slot_id=slot.id, content_record_id=ours.id))
    db.add(DecisionResolutionDB(decision_slot_id=slot.id, content_record_id=theirs.id))
    db.add(DecisionResolutionDB(decision_slot_id=slot.id, content_record_id=theirs.id))
    db.commit()

    yield {"category": category, "ours": default_brand, "theirs": other,
           "people": people, "content": {"ours": ours, "theirs": theirs}}

    db.rollback()
    ids = [p.id for p in people]
    db.query(SignalContributionDB).filter(SignalContributionDB.recipient_id.in_(ids)).delete(
        synchronize_session=False)
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(ids)).delete(
        synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
    db.query(DecisionResolutionDB).filter(
        DecisionResolutionDB.content_record_id.in_([ours.id, theirs.id])).delete(
        synchronize_session=False)
    db.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.category_id == category.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_([ours.id, theirs.id])).delete(
        synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id == category.id).delete()
    db.commit()


def _figures(db, world, brand):
    return category_graph(db, brand_id=brand.id)["metrics"][world["category"].id]


def test_signal_impact_sums_only_this_brands_audience(db, world):
    ours = _figures(db, world, world["ours"])
    theirs = _figures(db, world, world["theirs"])
    assert ours["total_delta"] == 3.0, "expected the email and the push subscriber, nobody else"
    assert ours["update_count"] == 2
    assert theirs["total_delta"] == 4.0


def test_content_and_selection_counts_are_this_brands(db, world):
    ours = _figures(db, world, world["ours"])
    theirs = _figures(db, world, world["theirs"])
    assert (ours["content_count"], ours["selected_count"]) == (1, 1)
    assert (theirs["content_count"], theirs["selected_count"]) == (1, 2)


def test_every_category_appears_because_the_taxonomy_is_shared(db, world):
    """ADR-150: one vocabulary. An empty brand sees the category, at zero."""
    graph = category_graph(db, brand_id=world["theirs"].id)
    assert world["category"].id in {c.id for c in graph["categories"]}


def test_the_page_renders_for_the_working_brand(db, world, default_brand):
    user = auth.create_user(db, email=f"graph-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="viewer")
    token = auth.create_session(db, user)
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    try:
        page = client.get("/ui/graph")
        assert page.status_code == 200, page.text[:300]
        assert world["category"].name in page.text
    finally:
        from sqlalchemy import text

        db.rollback()
        for table in ("auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.commit()


def test_edges_count_this_brands_content_and_audience(db, world):
    """Co-occurrence and edge impact mix both sources on one canvas, which is
    why ADR-150 said the edge metrics ship with the node ones."""
    from app.delivery.db_models import DeliveryExecutionDB
    from app.insight.db_models import EngagementEventDB

    second = CategoryDB(name=f"graph-b-{uuid.uuid4().hex[:8]}", type="main")
    db.add(second)
    db.flush()
    for record in world["content"].values():
        db.add(ContentCategoryAssignmentDB(content_id=record.id, category_id=second.id, score=1))
    execution = db.query(DeliveryExecutionDB).order_by(DeliveryExecutionDB.id).first()
    assert execution is not None, "the seed left no delivery execution for an event"
    events = {}
    for side in ("ours", "theirs"):
        event = EngagementEventDB(delivery_execution_id=execution.id, event_type="click",
                                  event_data={"content_record_id": world["content"][side].id})
        db.add(event)
        db.flush()
        events[side] = event
    in_ours, _push, in_theirs, nobody = world["people"]
    linked = [
        SignalContributionDB(recipient_id=in_ours.id, category_id=world["category"].id,
                             contribution_type="click", base_weight=16.0, event_id=events["ours"].id),
        SignalContributionDB(recipient_id=in_theirs.id, category_id=world["category"].id,
                             contribution_type="click", base_weight=32.0, event_id=events["theirs"].id),
        # Outside every audience, on our content: must count nowhere.
        SignalContributionDB(recipient_id=nobody.id, category_id=world["category"].id,
                             contribution_type="click", base_weight=64.0, event_id=events["ours"].id),
    ]
    db.add_all(linked)
    db.commit()
    try:
        def edge(brand):
            pair = {world["category"].id, second.id}
            found = [e for e in category_graph(db, brand_id=brand.id)["edges"]
                     if {e["source"], e["target"]} == pair]
            assert len(found) == 1, found
            return found[0]

        ours, theirs = edge(world["ours"]), edge(world["theirs"])
        assert ours["cooccurrence_count"] == theirs["cooccurrence_count"] == 1
        assert (ours["total_delta"], ours["event_count"]) == (16.0, 1)
        assert (theirs["total_delta"], theirs["event_count"]) == (32.0, 1)
    finally:
        db.rollback()
        db.query(SignalContributionDB).filter(
            SignalContributionDB.id.in_([c.id for c in linked])).delete(synchronize_session=False)
        db.query(EngagementEventDB).filter(
            EngagementEventDB.id.in_([e.id for e in events.values()])).delete(synchronize_session=False)
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.category_id == second.id).delete()
        db.query(CategoryDB).filter(CategoryDB.id == second.id).delete()
        db.commit()


def _graph_over_json(brand):
    from app.auth.permissions import VIEW
    from main import app
    from tests.machine import machine

    client = TestClient(app, raise_server_exceptions=False)
    with machine([VIEW], brand_id=brand.id) as headers:
        response = client.get("/insight/category-graph", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_json_graph_is_the_declared_brands(world):
    """Same figures as the service, per brand — a machine declaring brand B
    sees brand B's audience and content, not the default brand's."""
    def node(body):
        return next(n for n in body["nodes"] if n["id"] == world["category"].id)

    ours, theirs = _graph_over_json(world["ours"]), _graph_over_json(world["theirs"])
    assert ours["brand_id"] == world["ours"].id and theirs["brand_id"] == world["theirs"].id
    assert (node(ours)["total_delta"], node(ours)["content_count"], node(ours)["selected_count"]) == (3.0, 1, 1)
    assert (node(theirs)["total_delta"], node(theirs)["content_count"], node(theirs)["selected_count"]) == (4.0, 1, 2)


def test_the_json_graph_carries_no_layout(world):
    body = _graph_over_json(world["ours"])
    node = body["nodes"][0]
    assert not {"x", "y", "radius", "color"} & set(node), "layout is the client's"
