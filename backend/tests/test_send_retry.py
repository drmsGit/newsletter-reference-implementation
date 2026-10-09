"""A retry never sends again to someone already sent to (task-318).

A send that fails mid-batch commits each success as it goes, then is marked
failed so it can be retried (task-14). The retry walked every execution again,
so the recipients already sent to were mailed a second time and their provider
message id and delivery record (ADR-183, the as-sent evidence) were
overwritten. Found by the external review of 2026-10-09. A retry now skips an
execution already `sent`, before anything else, so not even a later
exclusion can overwrite what was sent.
"""
import pytest

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.delivery.service import send_send_instance
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip

# Borrowed fixtures: a real variant, consenting recipients, a snapshot and a
# recording mock provider, all cleaned up afterwards.
db = _render_skip.db
world = _render_skip.world


def _send_with(db, world, people):
    brand = world["brand"]
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-318", status="draft", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    for person in people:
        db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status="created",
                                   provider="mock", channel="email", purpose="marketing"))
    db.commit()
    return send


def _executions(db, send_id):
    db.expire_all()
    return {e.recipient_id: e for e in db.query(DeliveryExecutionDB).filter_by(send_instance_id=send_id)}


def test_a_retry_after_a_mid_batch_failure_does_not_resend_the_successes(db, world, monkeypatch):
    people = [world["person"](), world["person"]()]
    send = _send_with(db, world, people)
    capture = mock_module.MockProvider.send     # the world's recording provider
    calls = {"n": 0}

    def second_one_raises(self, address, artifact):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("provider fell over mid-batch")
        return capture(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", second_one_raises)
    with pytest.raises(RuntimeError):
        send_send_instance(db, send.id, brand_id=world["brand"].id)

    first = _executions(db, send.id)
    [done] = [e for e in first.values() if e.status == "sent"]
    done_id, done_message, done_record = done.recipient_id, done.provider_message_id, done.delivery_record
    db.refresh(db.get(SendInstanceDB, send.id))
    assert db.get(SendInstanceDB, send.id).status == "failed", "the failed send must be retryable"

    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    world["delivered"].clear()
    send_send_instance(db, send.id, brand_id=world["brand"].id)

    after = _executions(db, send.id)
    assert len(world["delivered"]) == 1, f"the retry mailed {len(world['delivered'])} people, not only the unfinished one"
    assert after[done_id].provider_message_id == done_message, "the original provider message id was overwritten"
    assert after[done_id].delivery_record == done_record, "the as-sent delivery record was overwritten"
    assert all(e.status == "sent" for e in after.values())
    assert db.get(SendInstanceDB, send.id).status == "sent"
    assert db.get(SendInstanceDB, send.id).sent_count == 2


def test_a_later_exclusion_does_not_overwrite_what_was_sent(db, world, monkeypatch):
    """A person sent to, then opted out before the retry, stays `sent`: the
    opt-out stops future mail, it does not rewrite the past."""
    from app.recipients.consent import record_consent

    people = [world["person"](), world["person"]()]
    send = _send_with(db, world, people)
    capture = mock_module.MockProvider.send
    calls = {"n": 0}

    def second_one_raises(self, address, artifact):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("provider fell over mid-batch")
        return capture(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", second_one_raises)
    with pytest.raises(RuntimeError):
        send_send_instance(db, send.id, brand_id=world["brand"].id)
    [done] = [e for e in _executions(db, send.id).values() if e.status == "sent"]
    record_consent(db, done.recipient_id, "opted_out", world["brand"].id, channel="email",
                   purpose="marketing", source="test")

    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    send_send_instance(db, send.id, brand_id=world["brand"].id)
    assert _executions(db, send.id)[done.recipient_id].status == "sent"
