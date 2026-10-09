"""An uncertain provider outcome stays non-retryable (task-318; ADR-183)."""
import pytest

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.delivery.service import send_send_instance
from tests import test_render_skip as fixtures

db = fixtures.db
world = fixtures.world


@pytest.mark.parametrize("known_success", [False, True])
def test_uncertain_delivery_is_never_retried_on_later_runs(db, world, monkeypatch, known_success):
    people = [world["person"]() for _ in range(2 if known_success else 1)]
    capture = mock_module.MockProvider.send
    calls = 0

    def accepted_without_answer(self, address, artifact):
        nonlocal calls
        calls += 1
        result = capture(self, address, artifact)
        if calls == len(people):
            raise RuntimeError("accepted remotely but response lost")
        return result

    monkeypatch.setattr(mock_module.MockProvider, "send", accepted_without_answer)
    with pytest.raises(RuntimeError, match="response lost"):
        world["send"](world["variant"](static=True, slots=0), people)
    send_id = world["made"]["sends"][-1]
    db.expire_all()
    rows = db.query(DeliveryExecutionDB).filter_by(send_instance_id=send_id).all()
    uncertain = [row for row in rows if row.status == "sending"]
    assert len(uncertain) == 1
    uncertain_id = uncertain[0].id
    known = {row.id: (row.provider_message_id, row.delivery_record) for row in rows if row.status == "sent"}
    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    expected_status = "partial_failed" if known_success else "failed"

    world["delivered"].clear()
    assert send_send_instance(db, send_id, brand_id=world["brand"].id) == expected_status
    assert world["delivered"] == []
    db.expire_all()
    unknown = db.get(DeliveryExecutionDB, uncertain_id)
    assert unknown.status == "uncertain"
    evidence = (unknown.unsubscribe_token, unknown.exclusion_reason)

    for _ in range(2):
        world["delivered"].clear()
        outcome = send_send_instance(db, send_id, brand_id=world["brand"].id)
        assert world["delivered"] == [], "a later retry contacted the uncertain recipient"
        assert outcome == expected_status
        db.expire_all()
        unknown = db.get(DeliveryExecutionDB, uncertain_id)
        assert unknown.status == "uncertain"
        assert (unknown.unsubscribe_token, unknown.exclusion_reason) == evidence
        parent = db.get(SendInstanceDB, send_id)
        assert (parent.sent_count, parent.failed_count) == (int(known_success), 1)
        for row_id, original in known.items():
            row = db.get(DeliveryExecutionDB, row_id)
            assert (row.provider_message_id, row.delivery_record) == original
