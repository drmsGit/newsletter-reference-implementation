"""Which records a decision slot chooses between (task-284).

ADR-179's addendum of 2026-10-05 point 3: a slot picks a record only if it is
machine ready AND marked ready for the slot's channel. ADR-174's addendum
(task-284, decided with the user): and only if its latest published version
fills every required field of the module the slot is bound to — nothing else
checks a slot's pick, because the send-time check skips slot modules. All of
it in `candidate_query`, so the count and every strategy agree.
"""
import uuid

import pytest

from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import slot_candidate_count
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentChannelReadinessDB, ContentRecordDB, ContentVersionDB,
)
from app.decision.strategies.registry import get_strategy

TAG = f"cand{uuid.uuid4().hex[:6]}"
COMPLETE = {"headline_medium": "Lisbon", "push_title": "Go", "push_body": "Now"}


@pytest.fixture
def world(db, default_brand):
    """A category of our own, and per channel a variant whose slot draws on it,
    bound to that channel's catalogue module."""
    category = CategoryDB(name=f"{TAG}-cat", type="main")
    campaign = CampaignDB(brand_id=default_brand.id, name=f"{TAG}-campaign")
    db.add_all([category, campaign]); db.flush()
    slots = {}
    for channel, module_type in (("email", "img_left"), ("push", "notification")):
        variant = VariantDB(campaign_id=campaign.id, channel=channel, name=channel, status="draft")
        db.add(variant); db.flush()
        slot = DecisionSlotDB(variant_id=variant.id, name=channel, decision_strategy="top_score",
                              candidate_filter={"category_ids": [category.id]}, max_results=1)
        db.add(slot); db.flush()
        db.add(ModuleInstanceDB(variant_id=variant.id, module_type=module_type, position=1,
                                decision_slot_id=slot.id))
        slots[channel] = slot
    db.commit()
    records = []

    def make(draft=COMPLETE, *, published=COMPLETE, machine_ready=True, ready_for=("email", "push")):
        record = ContentRecordDB(title=f"{TAG} record", content=dict(draft), status="active",
                                 brand_id=default_brand.id, machine_ready=machine_ready)
        db.add(record); db.flush()
        db.add(ContentCategoryAssignmentDB(content_id=record.id, category_id=category.id, score=7))
        if published is not None:
            db.add(ContentVersionDB(content_record_id=record.id, version_number=1,
                                    content=dict(published), created_by="test"))
        for channel in ready_for:
            db.add(ContentChannelReadinessDB(content_id=record.id, channel=channel, marked_by="test"))
        db.commit()
        records.append(record.id)
        return record.id

    yield {"make": make, "slots": slots, "brand": default_brand.id}
    db.rollback()
    ids = [s.id for s in slots.values()]
    variants = [s.variant_id for s in slots.values()]
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variants)).delete(synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.id.in_(ids)).delete(synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(variants)).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    for model, column in ((ContentChannelReadinessDB, ContentChannelReadinessDB.content_id),
                          (ContentCategoryAssignmentDB, ContentCategoryAssignmentDB.content_id),
                          (ContentVersionDB, ContentVersionDB.content_record_id),
                          (ContentRecordDB, ContentRecordDB.id)):
        db.query(model).filter(column.in_(records)).delete(synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id == category.id).delete()
    db.commit()


def _count(db, world, channel):
    return slot_candidate_count(db, world["slots"][channel].id, brand_id=world["brand"])["candidate_count"]


def _pick(db, world, channel):
    result = get_strategy("top_score").execute(db, world["slots"][channel])
    return result.content_record_id if result else None


def test_a_complete_machine_ready_record_marked_for_the_channel_is_picked(db, world):
    record = world["make"]()
    assert (_count(db, world, "email"), _pick(db, world, "email")) == (1, record)


@pytest.mark.parametrize("why, kwargs", [
    ("not machine ready", {"machine_ready": False}),
    ("marked for push only", {"ready_for": ("push",)}),
    ("never published", {"published": None}),
    ("its published headline is empty", {"published": {"headline_medium": ""}}),
    ("its published headline is only whitespace", {"published": {"headline_medium": " \n "}}),
    ("its published version has no headline at all", {"published": {"push_title": "Go"}}),
])
def test_each_condition_alone_keeps_a_record_out(db, world, why, kwargs):
    world["make"](**kwargs)
    assert (_count(db, world, "email"), _pick(db, world, "email")) == (0, None), why


def test_what_counts_is_the_published_version_not_the_draft(db, world):
    """A slot's pick renders the latest published version, so that is what must be complete."""
    world["make"](draft={}, published=COMPLETE)
    world["make"](draft=COMPLETE, published={})
    assert _count(db, world, "email") == 1


def test_the_latest_version_decides_not_an_earlier_one(db, world):
    record = world["make"]()  # version 1 is complete
    db.add(ContentVersionDB(content_record_id=record, version_number=2, content={}, created_by="test"))
    db.commit()
    assert _count(db, world, "email") == 0


def test_a_push_slot_finds_nothing_until_a_person_marks_push(db, world):
    world["make"](ready_for=("email",))
    assert _count(db, world, "push") == 0
    world["make"](ready_for=("email", "push"), published={"push_title": "Go"})  # no push text
    assert _count(db, world, "push") == 0
    record = world["make"](ready_for=("push",))
    assert (_count(db, world, "push"), _pick(db, world, "push")) == (1, record)


def test_a_slot_bound_to_no_module_asks_no_field(db, world):
    db.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.decision_slot_id == world["slots"]["email"].id).delete()
    db.commit()
    world["make"](published={})
    world["make"](published=None)
    assert _count(db, world, "email") == 1, "published but empty counts; never published does not"


def test_the_seeded_slots_still_resolve(db):
    """The demo seed marks its slot content machine ready and ready for email."""
    slots = db.query(DecisionSlotDB).all()
    assert slots, "the seeded test database has no decision slot"
    from app.decision.strategies.base import sending_brand_id

    for slot in slots:
        assert slot_candidate_count(db, slot.id, brand_id=sending_brand_id(db, slot))["candidate_count"] > 0
