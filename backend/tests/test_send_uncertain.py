"""A recipient whose provider call may have gone through is never sent again (task-318, AC #3).

Decided by the user 2026-10-09: when the provider was called and gave no
answer — an exception after the request may have been accepted — a retry
SKIPS that recipient rather than risk a duplicate; a large group of these is
checked and resent by hand (paste them into an audience group, plan a new
send). So the send marks each execution `sending`, committed, immediately
before the provider call: a later run finds it there and records it
`uncertain` instead of calling the provider again. Work never attempted is
still sent on retry. Uncertain counts as not delivered, and the executions
list filters by it.
"""
import pytest

from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.delivery.service import page_delivery_executions_for_send_instance, send_send_instance
from app.pagination import PageParams
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


def _planned(db, world, people) -> SendInstanceDB:
    brand = world["brand"]
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-318 ac3", status="draft", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    for person in people:
        db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status="created",
                                   provider="mock", channel="email", purpose="marketing"))
    db.commit()
    return send


def _rows(send_id):
    check = SessionLocal()
    try:
        return {e.recipient_id: (e.status, e.exclusion_reason, e.unsubscribe_token)
                for e in check.query(DeliveryExecutionDB).filter_by(send_instance_id=send_id)}
    finally:
        check.close()


@pytest.fixture
def second_provider_call_raises(monkeypatch):
    capture = mock_module.MockProvider.send
    calls = {"n": 0}

    def raising(self, address, artifact):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("provider gave no answer")
        return capture(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", raising)
    return lambda: monkeypatch.setattr(mock_module.MockProvider, "send", capture)


def test_a_recipient_whose_provider_call_raised_is_never_sent_again(db, world, second_provider_call_raises):
    people = [world["person"](), world["person"]()]
    send = _planned(db, world, people)
    with pytest.raises(RuntimeError):
        send_send_instance(db, send.id, brand_id=world["brand"].id)

    first = _rows(send.id)
    [maybe] = [rid for rid, (status, _, _) in first.items() if status == "sending"]
    assert first[maybe][2], "the unsubscribe token is committed before the mail can leave"

    second_provider_call_raises()           # the provider works again
    world["delivered"].clear()
    outcome = send_send_instance(db, send.id, brand_id=world["brand"].id)

    after = _rows(send.id)
    assert world["delivered"] == [], "the retry called the provider again for a maybe-sent recipient"
    status, reason, _ = after[maybe]
    assert status == "uncertain" and "not sent again" in reason
    db.expire_all()
    parent = db.get(SendInstanceDB, send.id)
    assert outcome == "partial_failed" == parent.status
    assert (parent.sent_count, parent.failed_count) == (1, 1)


def test_work_never_attempted_is_still_sent_on_retry(db, world, monkeypatch):
    """The failure comes before the provider call, so nothing could have left."""
    import app.rendering.frame as frame

    people = [world["person"](), world["person"]()]
    send = _planned(db, world, people)
    real = frame.render_frame
    calls = {"n": 0}

    def second_render_fails(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("render fell over")
        return real(*args, **kwargs)

    monkeypatch.setattr(frame, "render_frame", second_render_fails)
    with pytest.raises(RuntimeError):
        send_send_instance(db, send.id, brand_id=world["brand"].id)
    assert sorted(s for s, _, _ in _rows(send.id).values()) == ["created", "sent"]

    monkeypatch.setattr(frame, "render_frame", real)
    world["delivered"].clear()
    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "sent"
    assert len(world["delivered"]) == 1


def test_the_executions_list_finds_the_uncertain_ones(db, world, second_provider_call_raises):
    people = [world["person"](), world["person"]()]
    send = _planned(db, world, people)
    with pytest.raises(RuntimeError):
        send_send_instance(db, send.id, brand_id=world["brand"].id)
    second_provider_call_raises()
    send_send_instance(db, send.id, brand_id=world["brand"].id)

    page = page_delivery_executions_for_send_instance(
        db, send.id, PageParams(limit=50, offset=0), brand_id=world["brand"].id, status="uncertain")
    assert [e.status for e in page.items] == ["uncertain"]
    assert page.total == 1
