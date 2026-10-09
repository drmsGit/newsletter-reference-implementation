"""Audience changes preserve delivery evidence (task-328, ADR-176/183)."""
import pytest

from app.audience.db_models import AudienceGroupMemberDB
from app.delivery.db_models import DeliveryExecutionDB
from app.delivery.service import send_send_instance
from app.delivery.providers import mock as mock_module
from app.delivery.providers.base import SendResult
from tests import test_render_skip as _fixtures

db = _fixtures.db
world = _fixtures.world


@pytest.mark.parametrize("initial,expected", [
    ("sent", "sent"),
    ("uncertain", "uncertain"),
    ("sending", "uncertain"),
])
def test_leaving_and_rejoining_never_replays_a_known_or_possible_delivery(db, world, monkeypatch, initial, expected):
    from tests.test_retry_audience import _planned_to_group

    person, retryable = world["person"](), world["person"]()
    send, group = _planned_to_group(db, world, [person, retryable])
    calls = []

    def refused(self, address, artifact):
        calls.append(address)
        return SendResult(success=False, message="definite refusal keeps the send retryable")

    monkeypatch.setattr(mock_module.MockProvider, "send", refused)
    execution = db.query(DeliveryExecutionDB).filter_by(
        send_instance_id=send.id, recipient_id=person.id,
    ).one()
    execution_id = execution.id
    execution.status = initial
    execution.provider_message_id = "original-provider-evidence" if initial == "sent" else None
    execution.exclusion_reason = "original uncertainty evidence" if initial == "uncertain" else None
    send.status = "failed"
    db.query(AudienceGroupMemberDB).filter_by(group_id=group.id, recipient_id=person.id).delete()
    db.commit()

    send_send_instance(db, send.id, brand_id=world["brand"].id)
    db.expire_all()
    row = db.get(DeliveryExecutionDB, execution_id)
    assert row.status == expected
    assert row.provider_message_id == ("original-provider-evidence" if initial == "sent" else None)
    if initial == "uncertain":
        assert row.exclusion_reason == "original uncertainty evidence"
    if initial == "sending":
        assert "provider outcome unknown" in row.exclusion_reason
    reason = row.exclusion_reason
    assert world["delivered"] == []

    db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=person.id))
    db.commit()
    send_send_instance(db, send.id, brand_id=world["brand"].id)
    db.expire_all()
    row = db.get(DeliveryExecutionDB, execution_id)
    assert row.status == expected
    assert row.exclusion_reason == reason
    assert row.provider_message_id == ("original-provider-evidence" if initial == "sent" else None)
    assert world["delivered"] == [], "rejoining must not resend a known or possible delivery"
    assert len(calls) == 2, "only the retryable companion is attempted on each run"
