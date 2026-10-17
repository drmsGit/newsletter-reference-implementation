"""A click credits content only when the event names it (task-45, ADR-182).

`_primary_content_id_for_delivery` used to attach a guessed "primary" record —
the latest personalized pick, else the first content-bound module — to every
webhook click and open, so in a multi-content mail a click on the fourth item
credited the first. Decided 2026-10-02: no guessing, no single-item exception;
an unidentified event is recorded and credits no category.
"""
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB
from app.providers.adapters.resend import NormalizedEvent
from app.providers.service import process_provider_webhook_event
from app.recipients.db_models import RecipientDB, SignalContributionDB
from app.snapshots.db_models import SnapshotDB


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def delivered(db):
    """One delivered email whose only content record is categorised — the
    single-item case, where a guess would be easiest to defend."""
    brand = ensure_default_brand(db)
    category = CategoryDB(name=f"attr-{uuid.uuid4().hex[:8]}", type="main")
    record = ContentRecordDB(title="attr", content={"headline_medium": "x"},
                             status="active", brand_id=brand.id)
    db.add_all([category, record]); db.flush()
    db.add(ContentCategoryAssignmentDB(content_id=record.id, category_id=category.id, score=5))
    campaign = CampaignDB(brand_id=brand.id, name=f"attr-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="sent")
    db.add(variant); db.flush()
    db.add(ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=1,
                            content_record_id=record.id, module_data={}))
    snapshot = SnapshotDB(variant_id=variant.id,
                          render_context={"frame_version": 1, "channel": "email", "modules": []})
    db.add(snapshot); db.flush()
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="attr",
                          status="sent", provider="resend")
    recipient = RecipientDB(external_id=f"attr-{uuid.uuid4()}", status="active")
    db.add_all([send, recipient]); db.flush()
    message_id = f"msg-{uuid.uuid4().hex}"
    execution = DeliveryExecutionDB(send_instance_id=send.id, recipient_id=recipient.id,
                                    status="sent", provider="resend", channel="email",
                                    purpose="marketing", provider_message_id=message_id,
                                    # What the message carried (ADR-183): a click may
                                    # credit only this (task-240).
                                    delivery_record={"snapshot_id": snapshot.id, "picks": [
                                        {"module_id": 0, "content_record_id": record.id}]})
    db.add(execution); db.commit()
    yield {"message_id": message_id, "recipient": recipient, "record": record,
           "execution": execution}
    db.rollback()
    event_ids = [e.id for e in db.query(EngagementEventDB).filter(
        EngagementEventDB.delivery_execution_id == execution.id)]
    db.query(SignalContributionDB).filter(SignalContributionDB.recipient_id == recipient.id).delete()
    if event_ids:
        db.query(EngagementEventDB).filter(EngagementEventDB.id.in_(event_ids)).delete(
            synchronize_session=False)
    db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.id == execution.id).delete()
    for model, key in ((SendInstanceDB, send.id), (RecipientDB, recipient.id),
                       (SnapshotDB, snapshot.id)):
        db.query(model).filter(model.id == key).delete()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.content_id == record.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
    db.query(CategoryDB).filter(CategoryDB.id == category.id).delete()
    db.commit()


def _click(db, world, **data):
    return process_provider_webhook_event(db, NormalizedEvent(
        provider="resend", provider_message_id=world["message_id"], event_type="click",
        provider_event_id=f"evt-{uuid.uuid4().hex}", event_data=data,
    ))


def test_an_unidentified_click_is_recorded_and_credits_nothing(db, delivered):
    result = _click(db, delivered, link="https://example.invalid/somewhere")
    assert result.status == "matched", result
    db.expire_all()
    assert db.query(EngagementEventDB).filter(
        EngagementEventDB.delivery_execution_id == delivered["execution"].id).count() == 1
    assert db.query(SignalContributionDB).filter(
        SignalContributionDB.recipient_id == delivered["recipient"].id).count() == 0, (
        "a click that did not name its content was credited to one anyway"
    )


def test_a_click_that_names_its_content_is_credited(db, delivered):
    """The path tracked links will use (ADR-102): the event says which content."""
    _click(db, delivered, content_record_id=delivered["record"].id)
    db.expire_all()
    assert db.query(SignalContributionDB).filter(
        SignalContributionDB.recipient_id == delivered["recipient"].id).count() == 1



def test_a_named_content_the_message_did_not_carry_is_not_credited(db, delivered):
    """A URL is text: a stale or edited link can name anything (task-240). The
    other record is real and categorised, so only the delivery-record check
    stands between it and a credit."""
    brand = ensure_default_brand(db)
    other = ContentRecordDB(title="not sent", content={}, status="active", brand_id=brand.id)
    category = CategoryDB(name=f"attr-other-{uuid.uuid4().hex[:6]}", type="main")
    db.add_all([other, category]); db.flush()
    db.add(ContentCategoryAssignmentDB(content_id=other.id, category_id=category.id, score=5))
    db.commit()
    try:
        _click(db, delivered, content_record_id=other.id)
        db.expire_all()
        assert db.query(SignalContributionDB).filter(
            SignalContributionDB.recipient_id == delivered["recipient"].id).count() == 0
    finally:
        db.rollback()
        db.query(SignalContributionDB).filter(SignalContributionDB.category_id == category.id).delete()
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.content_id == other.id).delete()
        db.query(ContentRecordDB).filter(ContentRecordDB.id == other.id).delete()
        db.query(CategoryDB).filter(CategoryDB.id == category.id).delete()
        db.commit()


def test_without_a_delivery_record_nothing_can_be_verified_or_credited(db, delivered):
    execution = db.get(DeliveryExecutionDB, delivered["execution"].id)
    execution.delivery_record = None
    db.commit()
    _click(db, delivered, content_record_id=delivered["record"].id)
    db.expire_all()
    assert db.query(SignalContributionDB).filter(
        SignalContributionDB.recipient_id == delivered["recipient"].id).count() == 0
