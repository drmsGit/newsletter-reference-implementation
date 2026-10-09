"""Retry consent and immutable success interact correctly (task-318; ADR-163/183)."""
import pytest

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.service import send_send_instance
from app.recipients.consent import record_consent
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as fixtures

db = fixtures.db
world = fixtures.world


def test_retry_after_unfinished_recipient_opts_out_sends_nobody(db, world, monkeypatch):
    people = [world["person"](), world["person"]()]
    brand_id = world["brand"].id
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand_id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand_id,
                          name="retry consent regression", status="draft", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    for person in people:
        db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id,
                                  status="created", provider="mock", channel="email",
                                  purpose="marketing"))
    db.commit()
    # Interrupted before the second recipient's provider call (in its render),
    # so that recipient was never attempted. Since task-318 AC #3 a failure
    # INSIDE the provider call marks the recipient uncertain and is never
    # retried, so this test's case — an unattempted recipient who opts out
    # before the retry — needs the failure to come before the call.
    import app.rendering.frame as frame

    real_render = frame.render_frame
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("interrupted batch")
        return real_render(*args, **kwargs)

    monkeypatch.setattr(frame, "render_frame", fail_second)
    with pytest.raises(RuntimeError, match="interrupted batch"):
        send_send_instance(db, send.id, brand_id=brand_id)
    db.expire_all()
    rows = db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id).all()
    [done] = [row for row in rows if row.status == "sent"]
    [unfinished] = [row for row in rows if row.status != "sent"]
    original_id, original_record = done.provider_message_id, done.delivery_record
    record_consent(db, unfinished.recipient_id, "opted_out", brand_id,
                   channel="email", purpose="marketing", source="test")
    monkeypatch.setattr(frame, "render_frame", real_render)
    world["delivered"].clear()

    send_send_instance(db, send.id, brand_id=brand_id)

    db.expire_all()
    assert world["delivered"] == [], "retry mailed a completed or no-longer-consenting recipient"
    assert done.status == "sent"
    assert done.provider_message_id == original_id
    assert done.delivery_record == original_record
    assert unfinished.status == "excluded"
    assert unfinished.exclusion_reason
    assert send.status == "sent"
    assert send.sent_count == 1
    assert send.failed_count == 0
    assert send.excluded_count == 1
