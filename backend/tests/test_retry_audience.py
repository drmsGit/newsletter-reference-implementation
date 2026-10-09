"""A retry sends only to people still in the send's audience (task-328).

Every send re-resolves its audience group right before firing (ADR-176 point
4), but reconciliation dropped a no-longer-matching recipient only while their
execution was still `created`. A `failed` one stayed — and the retry mailed a
person the current audience no longer includes. Found by ChatGPT 2026-10-09
(draft-3). The send loop now enforces the current membership for every
execution not yet final: someone outside it is recorded `excluded` at the
"audience" stage, keeping the trace of the earlier attempt; someone who
rejoins is sent to.
"""
import uuid

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.delivery.db_models import DeliveryExecutionDB
from app.delivery.exclusion import STAGE_AUDIENCE
from app.delivery.providers import mock as mock_module
from app.delivery.providers.base import SendResult
from app.delivery.service import prepare_send_from_audience, send_instance_detail, send_send_instance
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


def _planned_to_group(db, world, people):
    brand = world["brand"]
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    group = AudienceGroupDB(brand_id=brand.id, name=f"task-328-{uuid.uuid4().hex[:4]}")
    db.add(group)
    db.flush()
    world["made"]["groups"].append(group.id)
    for person in people:
        db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=person.id))
    db.commit()
    send = prepare_send_from_audience(db, snapshot.id, "task-328", group.id, "mock", brand_id=brand.id)
    world["made"]["sends"].append(send.id)
    return send, group


def _status(db, send_id, recipient_id):
    db.expire_all()
    row = (db.query(DeliveryExecutionDB)
           .filter_by(send_instance_id=send_id, recipient_id=recipient_id).one())
    return row.status, row.exclusion_reason


def test_a_failed_recipient_who_left_the_audience_is_not_mailed_on_retry(db, world, monkeypatch):
    stays, leaves = world["person"](), world["person"]()
    send, group = _planned_to_group(db, world, [stays, leaves])
    leaver_address = None
    capture = mock_module.MockProvider.send

    def leaver_refused(self, address, artifact):
        nonlocal leaver_address
        if leaver_address is None and calls["n"] == 1:
            leaver_address = address
        calls["n"] += 1
        return SendResult(success=False, message="mailbox full")

    calls = {"n": 0}
    monkeypatch.setattr(mock_module.MockProvider, "send", leaver_refused)
    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "failed"

    db.query(AudienceGroupMemberDB).filter_by(group_id=group.id, recipient_id=leaves.id).delete()
    db.commit()
    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    world["delivered"].clear()
    send_send_instance(db, send.id, brand_id=world["brand"].id)

    assert len(world["delivered"]) == 1, "the retry mailed someone the audience no longer includes"
    status, reason = _status(db, send.id, leaves.id)
    assert status == "excluded" and reason.startswith(f"{STAGE_AUDIENCE}:")
    assert _status(db, send.id, stays.id)[0] == "sent"
    assert send_instance_detail(db, send.id, brand_id=world["brand"].id).exclusions_by_stage == {STAGE_AUDIENCE: 1}


def test_someone_who_rejoins_before_a_later_retry_is_sent_to(db, world, monkeypatch):
    person = world["person"]()
    send, group = _planned_to_group(db, world, [person])
    capture = mock_module.MockProvider.send
    monkeypatch.setattr(mock_module.MockProvider, "send",
                        lambda self, address, artifact: SendResult(success=False, message="mailbox full"))
    send_send_instance(db, send.id, brand_id=world["brand"].id)

    member = db.query(AudienceGroupMemberDB).filter_by(group_id=group.id, recipient_id=person.id).one()
    db.delete(member)
    db.commit()
    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    send_send_instance(db, send.id, brand_id=world["brand"].id)
    assert _status(db, send.id, person.id)[0] == "excluded"

    db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=person.id))
    db.commit()
    world["delivered"].clear()
    send_send_instance(db, send.id, brand_id=world["brand"].id)
    assert _status(db, send.id, person.id) == ("sent", None)
    assert len(world["delivered"]) == 1
