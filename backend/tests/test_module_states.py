"""The render response says what each module is doing (task-227).

Variant Editor interview 4.4: three slot states, with "found nothing" visibly
different — it is the only one that means "your rule is wrong", and the only
one that otherwise ships as a silently shorter email. 4.2: a preview for a
named recipient that falls back to the generic pick says so. 4.3: a preview
shows unpublished edits. An HTML comment in the artifact is not something a
client should parse, so the state comes back structured.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import VIEW
from app.campaigns.db_models import (
    CampaignDB, DecisionResolutionDB, DecisionSlotDB, ModuleInstanceDB, VariantDB,
)
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentChannelReadinessDB, ContentRecordDB, ContentVersionDB,
)
from app.recipients.db_models import RecipientDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def world(db, default_brand):
    b = default_brand.id
    campaign = CampaignDB(brand_id=b, name=f"ms-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    category = CategoryDB(name=f"ms-{uuid.uuid4().hex[:6]}")
    empty_category = CategoryDB(name=f"ms-empty-{uuid.uuid4().hex[:6]}")
    # The slots' candidate: one a slot may take (task-284).
    published = ContentRecordDB(title="pub", content={"headline_medium": "Same"}, status="active", brand_id=b,
                                machine_ready=True)
    drafted = ContentRecordDB(title="draft", content={"headline_medium": "Edited"}, status="active", brand_id=b)
    recipient = RecipientDB(external_id=f"ms-{uuid.uuid4().hex[:8]}")
    db.add_all([variant, category, empty_category, published, drafted, recipient]); db.flush()
    db.add_all([
        ContentVersionDB(content_record_id=published.id, version_number=1, content={"headline_medium": "Same"}),
        ContentVersionDB(content_record_id=drafted.id, version_number=1, content={"headline_medium": "Old"}),
        ContentCategoryAssignmentDB(content_id=published.id, category_id=category.id, score=5),
        ContentChannelReadinessDB(content_id=published.id, channel="email", marked_by="test"),
    ])
    slot = lambda name, cats: DecisionSlotDB(  # noqa: E731
        variant_id=variant.id, name=name, decision_type="content_recommendation",
        decision_strategy="top_score", candidate_filter={"category_ids": cats})
    resolved, unrun, nothing = slot("resolved", [category.id]), slot("unrun", [category.id]), \
        slot("nothing", [empty_category.id])
    db.add_all([resolved, unrun, nothing]); db.flush()
    db.add(DecisionResolutionDB(decision_slot_id=resolved.id, recipient_id=None,
                                content_record_id=published.id, reason="r", score=1))
    # An old pick, from before the rule was narrowed to a category with nothing in it.
    db.add(DecisionResolutionDB(decision_slot_id=nothing.id, recipient_id=None,
                                content_record_id=published.id, reason="r", score=1))
    modules = [
        ModuleInstanceDB(variant_id=variant.id, module_type="envelope", position=0, module_data={"subject": "S"}),
        ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=1, content_record_id=published.id),
        ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=2, content_record_id=drafted.id),
        ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=3, decision_slot_id=resolved.id),
        ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=4, decision_slot_id=unrun.id),
        ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=5, decision_slot_id=nothing.id),
        ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=6),
        ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=7, module_data={"label": "Go"}),
    ]
    db.add_all(modules); db.commit()
    yield {"variant": variant, "recipient": recipient, "modules": modules}
    db.rollback()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    slot_ids = [resolved.id, unrun.id, nothing.id]
    db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id.in_(slot_ids)).delete(
        synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.id.in_(slot_ids)).delete(synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.category_id == category.id).delete()
    db.query(ContentChannelReadinessDB).filter(ContentChannelReadinessDB.content_id == published.id).delete()
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id.in_([published.id, drafted.id])).delete(
        synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_([published.id, drafted.id])).delete(
        synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id.in_([category.id, empty_category.id])).delete(
        synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
    db.commit()


def _states(variant_id, **params):
    with machine([VIEW]) as headers:
        response = client.get(f"/rendering/variants/{variant_id}", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return {m["position"]: m for m in response.json()["modules"]}


def test_each_kind_of_module_says_what_it_is(world):
    states = _states(world["variant"].id)
    assert 0 not in states, "the envelope is the variant's, not a module in the stack"
    assert [states[p]["kind"] for p in range(1, 8)] == \
        ["record", "record", "slot", "slot", "slot", "unbound", "typed"]


def test_three_slot_states_with_found_nothing_apart(world):
    states = _states(world["variant"].id)
    assert states[3]["slot_state"] == "resolved"
    assert states[4]["slot_state"] == "not_run"
    # An old pick exists, but the rule now matches nothing: that is the finding.
    assert states[5]["slot_state"] == "finds_nothing"


def test_a_named_recipient_without_their_own_pick_is_told_it_is_the_generic_one(world):
    generic = _states(world["variant"].id)
    named = _states(world["variant"].id, recipient_id=world["recipient"].id)
    assert generic[3]["generic_pick"] is False, "nobody was named, so nothing fell back"
    assert named[3]["generic_pick"] is True


def test_a_record_with_unpublished_edits_says_so(world):
    states = _states(world["variant"].id)
    assert (states[1]["unpublished_changes"], states[2]["unpublished_changes"]) == (False, True)


def test_required_fields_left_empty_are_named(world):
    states = _states(world["variant"].id)
    assert states[7]["missing_required"] == ["url"], "cta requires label and url; only url is empty"
    assert states[1]["missing_required"] == [] or "headline_medium" not in states[1]["missing_required"]


def test_another_brands_variant_is_not_found(world, foreign_api):
    with foreign_api([VIEW]) as headers:
        response = client.get(f"/rendering/variants/{world['variant'].id}", headers=headers)
    assert response.status_code == 404, response.text


def test_a_slot_that_picked_only_per_recipient_is_not_called_unrun(db, world):
    """A per-recipient strategy writes picks for named people and none for
    "anyone", so a generic preview finds nothing to show. "Not run" would be
    false — it ran (found live on the dev data, 2026-10-04)."""
    unrun = world["modules"][4]
    db.add(DecisionResolutionDB(decision_slot_id=unrun.decision_slot_id, recipient_id=world["recipient"].id,
                                content_record_id=world["modules"][1].content_record_id, reason="r", score=1))
    db.commit()
    assert _states(world["variant"].id)[4]["slot_state"] == "per_recipient"
    named = _states(world["variant"].id, recipient_id=world["recipient"].id)[4]
    assert (named["slot_state"], named["generic_pick"]) == ("resolved", False)
