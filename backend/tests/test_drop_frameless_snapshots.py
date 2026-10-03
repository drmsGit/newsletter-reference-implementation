"""`scripts/drop_frameless_snapshots.py` (ADR-183 point 6).

It deletes data, so two things are pinned: it removes exactly a frameless
snapshot and what hangs off it, leaving frames alone; and the foreign keys it
walks are all the foreign keys there are — a new one would make it either fail
or leave rows pointing at nothing.
"""
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, VariantDB
from app.database import Base, SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB
from app.recipients.db_models import RecipientDB, SignalContributionDB
from app.rendering.frame import build_frame
from app.snapshots.db_models import SnapshotDB
from scripts import drop_frameless_snapshots as script


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_every_foreign_key_into_the_dropped_tables_is_handled():
    import main  # noqa: F401 — registers every model

    targets = {"snapshots", "send_instances", "delivery_executions", "engagement_events"}
    found = {
        f"{table.name}.{fk.parent.name}"
        for table in Base.metadata.sorted_tables
        for fk in table.foreign_keys
        if fk.column.table.name in targets
    }
    assert found == {
        "send_instances.snapshot_id", "content_overrides.send_instance_id",
        "delivery_executions.send_instance_id", "engagement_events.delivery_execution_id",
        "signal_contributions.event_id",
    }, f"a foreign key appeared that the drop script does not handle: {found}"


def test_it_drops_a_frameless_snapshot_and_its_chain_and_keeps_frames(db, tmp_path):
    from app.content.db_models import CategoryDB

    brand = ensure_default_brand(db)
    campaign = CampaignDB(brand_id=brand.id, name=f"drop-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.flush()
    old = SnapshotDB(variant_id=variant.id, render_context={})
    kept = SnapshotDB(variant_id=variant.id,
                      render_context=build_frame(db, variant.id))
    recipient = RecipientDB(external_id=f"drop-{uuid.uuid4()}", status="active")
    category = CategoryDB(name=f"drop-{uuid.uuid4().hex[:6]}", type="main")
    db.add_all([old, kept, recipient, category]); db.flush()
    send = SendInstanceDB(snapshot_id=old.id, brand_id=brand.id, name="old", status="sent",
                          provider="mock")
    db.add(send); db.flush()
    execution = DeliveryExecutionDB(send_instance_id=send.id, recipient_id=recipient.id,
                                    status="sent", provider="mock", channel="email",
                                    purpose="marketing")
    db.add(execution); db.flush()
    event = EngagementEventDB(delivery_execution_id=execution.id, event_type="click")
    db.add(event); db.flush()
    contribution = SignalContributionDB(recipient_id=recipient.id, category_id=category.id,
                                        contribution_type="click", base_weight=5, event_id=event.id)
    db.add(contribution); db.commit()
    (tmp_path / "old.html").write_text("<html></html>")
    # Ids captured now: the rows are about to be deleted, and reading an
    # attribute of a deleted instance raises.
    old_id, kept_id, send_id = old.id, kept.id, send.id
    chain = ((SendInstanceDB, send.id), (DeliveryExecutionDB, execution.id),
             (EngagementEventDB, event.id), (SignalContributionDB, contribution.id))
    recipient_id, category_id, variant_id, campaign_id = recipient.id, category.id, variant.id, campaign.id
    try:
        ids = script.plan(db, storage=tmp_path)
        assert old_id in ids["snapshots"] and kept_id not in ids["snapshots"]
        assert send_id in ids["send_instances"]
        script.apply(db, ids)
        db.expire_all()
        assert db.get(SnapshotDB, old_id) is None
        assert db.get(SnapshotDB, kept_id) is not None, "a frame was dropped"
        for model, key in chain:
            assert db.get(model, key) is None, model.__name__
        assert not (tmp_path / "old.html").exists()
    finally:
        db.rollback()
        db.query(SnapshotDB).filter(SnapshotDB.id.in_([old_id, kept_id])).delete(
            synchronize_session=False)
        db.query(RecipientDB).filter(RecipientDB.id == recipient_id).delete()
        db.query(CategoryDB).filter(CategoryDB.id == category_id).delete()
        db.query(VariantDB).filter(VariantDB.id == variant_id).delete()
        db.query(CampaignDB).filter(CampaignDB.id == campaign_id).delete()
        db.commit()
