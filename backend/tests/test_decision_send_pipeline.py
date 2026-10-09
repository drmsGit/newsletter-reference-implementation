"""Real decision/send eligibility and per-channel consent (task-320, task-321)."""
import uuid

import pytest

from app.campaigns.db_models import DecisionSlotDB
from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB, ContentChannelReadinessDB, ContentRecordDB
from app.decision.service import execute_decision_slot as real_execute
from app.delivery.exclusion import REASON_NOTHING_TO_SHOW, STAGE_RENDER
from tests import test_render_skip as fixtures

db = fixtures.db
world = fixtures.world


@pytest.mark.parametrize("channel", ["email", "push"])
def test_real_pick_sends_then_loss_of_readiness_does_not_reuse_it(db, world, monkeypatch, channel):
    variant = world["variant"](channel, slots=1)
    person = world["person"](channel)
    record_id = world["made"]["records"][0]
    record = db.get(ContentRecordDB, record_id)
    record.machine_ready = True
    category = CategoryDB(name=f"pipeline-{uuid.uuid4().hex}", type="main")
    db.add(category)
    db.flush()
    db.add(ContentCategoryAssignmentDB(content_id=record_id, category_id=category.id, score=10))
    db.add(ContentChannelReadinessDB(content_id=record_id, channel=channel, marked_by="test"))
    slot = db.query(DecisionSlotDB).filter_by(variant_id=variant.id).one()
    slot.candidate_filter = {"category_ids": [category.id]}
    db.commit()
    monkeypatch.setattr("app.decision.service.execute_decision_slot", real_execute)
    try:
        _, first = world["send"](variant, [person])
        assert first[person.id] == ("sent", None), "an eligible real pick must reach the provider"
        assert len(world["delivered"]) == 1
        db.query(ContentChannelReadinessDB).filter_by(content_id=record_id, channel=channel).delete()
        db.commit()

        _, second = world["send"](variant, [person])

        assert world["delivered"] == [], "current ineligibility reused a historical pick"
        assert second[person.id] == ("excluded", f"{STAGE_RENDER}: {REASON_NOTHING_TO_SHOW}")
    finally:
        db.rollback()
        db.query(ContentChannelReadinessDB).filter_by(content_id=record_id, channel=channel).delete()
        db.query(ContentCategoryAssignmentDB).filter_by(category_id=category.id).delete()
        db.query(CategoryDB).filter_by(id=category.id).delete()
        db.commit()
